# Secrets Management System Design

**Purpose**: Comprehensive design for secure secrets handling in sc-conductor  
**Scope**: Architecture, plugins, storage, rotation, audit, compliance  
**Version**: 1.0 | October 7, 2026

---

## 1. Secrets Management Architecture

### Principles

1. **Never commit secrets to git**
2. **Audit all secret access**
3. **Support multiple backends** (dev to enterprise)
4. **Graceful fallback** (convenience vs. security trade-offs)
5. **Automatic rotation** (for long-lived secrets)
6. **Compliance-ready** (SOC2, ISO27001, HIPAA)

### Architecture Diagram

```
Application
    ↓
SecretsManager (orchestrator)
    ↓
┌───────────────────────────────────┐
│   SecretsPlugin Interface         │
├───────────────────────────────────┤
│ • get_secret(key)                 │
│ • set_secret(key, value)          │
│ • rotate_secret(key)              │
│ • audit_log()                     │
└───────────────────────────────────┘
    ↓ (routes to appropriate backend)
┌─────────────────────────────────────────┐
│ Backends                                 │
├─────────────────────────────────────────┤
│ • EnvSecretsPlugin (env vars)           │
│ • LocalFileSecretsPlugin (encrypted)    │
│ • VaultSecretsPlugin (HashiCorp Vault)  │
│ • AwsSecretsPlugin (AWS Secrets Mgr)    │
│ • AzureSecretsPlugin (Azure Key Vault)  │
│ • KubernetesSecretsPlugin (K8s secrets) │
└─────────────────────────────────────────┘
```

---

## 2. Configurable Secrets Plugin

### Python Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SecretsConfig:
    """Fully configurable secrets management"""
    
    # Backend selection
    type: str = "local_file"  # env | local_file | vault | aws | azure | kubernetes
    
    # 1. Fallback behavior
    fallback_strategy: str = "fail"  # fail | env | none
    # fail = try backend first, fallback to env vars if unavailable
    # env = try env vars first, then backend
    # none = backend only, fail hard
    
    # 2. Caching strategy
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_file: Optional[str] = None
    refresh_before_expiry: bool = True  # Proactive refresh
    
    # 3. Multi-level access control
    read_only: bool = True
    can_rotate: bool = False
    is_admin: bool = False
    
    # 4. Rotation workflow
    rotation_enabled: bool = True
    rotation_schedule: str = "manual"  # manual | daily | weekly | monthly
    notify_on_rotation: bool = True
    grace_period_seconds: int = 60  # Time old secret remains valid
    
    # 5. Naming convention
    naming_convention: str = "hierarchy"  # flat | hierarchy | custom
    naming_prefix: str = "sc-conductor"
    naming_environment: str = "dev"
    naming_pattern: Optional[str] = None
    
    # Backend-specific config
    vault_addr: Optional[str] = None
    vault_namespace: Optional[str] = None
    vault_auth_method: str = "token"  # token | oidc | aws
    aws_region: str = "us-east-1"
    azure_vault_url: Optional[str] = None
    k8s_namespace: str = "default"
    
    # Audit and compliance
    audit_enabled: bool = True
    audit_retention_days: int = 90
    immutable_log: bool = False  # Append-only for compliance
    
    # Notification channels
    notify_channels: List[str] = None  # ["slack", "email"]


class SecretsPlugin(ABC):
    """Base class for secrets management (all backends implement this)"""
    
    def __init__(self, config: SecretsConfig):
        self.config = config
        self._cache: Dict[str, Tuple[str, float]] = {}  # (value, expiry)
        self._audit_log: List[Dict] = []
        self._scheduled_refreshes: Dict[str, float] = {}
    
    # Public API (same for all backends)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret with configured fallback, caching, audit logging.
        
        Respects:
        • fallback_strategy (fail/env/none)
        • cache_enabled and cache_ttl_seconds
        • RBAC: read_only blocks access if needed
        • Audit: Logs all accesses
        """
        # Check RBAC
        if self.config.read_only and key not in self._get_readable_keys():
            self._log_audit("denied_read", key, "read_only=true")
            raise PermissionError(f"Access denied to {key} (read_only)")
        
        # Implement fallback strategy
        secret = self._get_with_fallback(key)
        
        # Log access
        self._log_audit("read", key, success=(secret is not None))
        
        return secret if secret is not None else default
    
    def set_secret(self, key: str, value: str) -> None:
        """Set secret (requires read_write access)"""
        if self.config.read_only:
            raise PermissionError("Cannot set secrets: read_only=true")
        
        self._set_secret_backend(key, value)
        self._log_audit("set", key, success=True)
        
        # Invalidate cache
        if key in self._cache:
            del self._cache[key]
    
    def rotate_secret(self, key: str, new_value: Optional[str] = None) -> None:
        """
        Rotate secret with grace period.
        
        Process:
        1. Generate/accept new secret
        2. Store new value, mark old as deprecated
        3. Apply grace_period_seconds
        4. Remove old value
        5. Notify (if enabled)
        """
        if not self.config.rotation_enabled:
            raise PermissionError("Rotation disabled: rotation_enabled=false")
        
        if not self.config.can_rotate and not self.config.is_admin:
            raise PermissionError("Insufficient permissions to rotate")
        
        # Store new value
        self._set_secret_backend(f"{key}_new", new_value or self._generate_secret())
        self._log_audit("rotate_start", key)
        
        # Grace period: old secret remains active
        self._apply_grace_period(key)
        
        # Cleanup old secret
        self._cleanup_old_secret(key)
        self._log_audit("rotate_complete", key)
        
        # Notify
        if self.config.notify_on_rotation:
            self._notify_rotation(key)
    
    def list_secrets(self) -> Dict[str, Dict[str, Any]]:
        """List all secrets (admin only, for audit)"""
        if not self.config.is_admin:
            raise PermissionError("Only admins can list secrets")
        
        return self._list_secrets_backend()
    
    def get_audit_log(self, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> List[Dict]:
        """Get audit log of all secret accesses"""
        logs = self._audit_log
        
        if start_time:
            logs = [l for l in logs if l['timestamp'] >= start_time]
        if end_time:
            logs = [l for l in logs if l['timestamp'] <= end_time]
        
        return logs
    
    # Internal implementation (framework handles these)
    
    def _get_with_fallback(self, key: str) -> Optional[str]:
        """Apply fallback strategy"""
        if self.config.fallback_strategy == "none":
            return self._get_cached_or_fetch(key)
        
        elif self.config.fallback_strategy == "env":
            # Try env var first
            env_val = os.environ.get(f"SC_CONDUCTOR_{key.upper()}")
            if env_val:
                return env_val
            # Fall through to backend
            return self._get_cached_or_fetch(key)
        
        elif self.config.fallback_strategy == "fail":
            # Try backend first
            try:
                return self._get_cached_or_fetch(key)
            except Exception as e:
                # Fallback to env var
                env_val = os.environ.get(f"SC_CONDUCTOR_{key.upper()}")
                if env_val:
                    self._log_audit("fallback_to_env", key)
                    return env_val
                # No fallback available, raise original error
                raise e
    
    def _get_cached_or_fetch(self, key: str) -> Optional[str]:
        """Apply caching strategy with proactive refresh"""
        if not self.config.cache_enabled:
            return self._fetch_secret(key)
        
        now = time.time()
        
        # Check cache
        if key in self._cache:
            value, expiry = self._cache[key]
            if now < expiry:
                # In cache and not expired
                # Check if should proactively refresh
                if self.config.refresh_before_expiry:
                    refresh_at = expiry - 30  # Refresh 30s before expiry
                    if now > refresh_at:
                        self._schedule_refresh(key)
                return value
            else:
                # Expired, remove
                del self._cache[key]
        
        # Fetch fresh
        value = self._fetch_secret(key)
        
        # Cache it
        if value and self.config.cache_enabled:
            expiry = now + self.config.cache_ttl_seconds
            self._cache[key] = (value, expiry)
        
        return value
    
    def _log_audit(self, action: str, key: str, details: str = "", 
                   success: bool = True) -> None:
        """Log to audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "key": key,
            "details": details,
            "success": success,
            "user": os.environ.get("USER", "unknown"),
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "source": "secrets_plugin"
        }
        
        self._audit_log.append(log_entry)
        
        # If immutable log, persist immediately
        if self.config.immutable_log:
            self._persist_audit_entry(log_entry)
    
    def _apply_grace_period(self, key: str) -> None:
        """Apply grace period where old secret is still valid"""
        if self.config.grace_period_seconds <= 0:
            return
        
        print(f"🔄 Grace period: Old secret remains valid for "
              f"{self.config.grace_period_seconds}s")
        time.sleep(self.config.grace_period_seconds)
    
    def _notify_rotation(self, key: str) -> None:
        """Notify relevant systems of rotation"""
        if not self.config.notify_channels:
            return
        
        message = f"Secret rotated: {key}"
        
        for channel in self.config.notify_channels:
            if channel == "slack":
                self._notify_slack(message)
            elif channel == "email":
                self._notify_email(message)
    
    # Abstract methods (must implement in subclass)
    
    @abstractmethod
    def _fetch_secret(self, key: str) -> Optional[str]:
        """Backend-specific secret retrieval"""
        pass
    
    @abstractmethod
    def _set_secret_backend(self, key: str, value: str) -> None:
        """Backend-specific secret storage"""
        pass
    
    @abstractmethod
    def _list_secrets_backend(self) -> Dict[str, Dict[str, Any]]:
        """Backend-specific secret listing"""
        pass
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        return "base_secrets"
```

---

## 3. Secrets Backend Implementations

### 3.1 Environment Variables Plugin

```python
class EnvSecretsPlugin(SecretsPlugin):
    """Read secrets from environment variables (default, no setup)"""
    
    def _fetch_secret(self, key: str) -> Optional[str]:
        env_key = f"SC_CONDUCTOR_{key.upper()}"
        return os.environ.get(env_key)
    
    def _set_secret_backend(self, key: str, value: str) -> None:
        raise PermissionError(
            f"Cannot set env var programmatically.\n"
            f"Use: export SC_CONDUCTOR_{key.upper()}=value"
        )
    
    def _list_secrets_backend(self) -> Dict[str, Dict]:
        return {
            k: {"source": "env", "readable": True}
            for k, v in os.environ.items()
            if k.startswith("SC_CONDUCTOR_")
        }
    
    def get_plugin_name(self) -> str:
        return "env"
```

**Use case**: Local development, CI/CD with environment variables

**Setup**:
```bash
export SC_CONDUCTOR_JIRA_TOKEN="abc123"
export SC_CONDUCTOR_SLACK_WEBHOOK="https://..."
sc-conductor run --all
```

---

### 3.2 Local Encrypted File Plugin

```python
import json
from cryptography.fernet import Fernet
import hashlib

class LocalFileSecretsPlugin(SecretsPlugin):
    """Encrypt secrets in local file (~/.sc-conductor/secrets.enc)"""
    
    def __init__(self, config: SecretsConfig):
        super().__init__(config)
        self.secrets_file = os.path.expanduser("~/.sc-conductor/secrets.enc")
        self.key_file = os.path.expanduser("~/.sc-conductor/key.bin")
        self.cipher = self._load_or_create_cipher()
    
    def _load_or_create_cipher(self) -> Fernet:
        """Load existing key or create new"""
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Only user can read
        
        return Fernet(key)
    
    def _fetch_secret(self, key: str) -> Optional[str]:
        if not os.path.exists(self.secrets_file):
            return None
        
        with open(self.secrets_file, 'rb') as f:
            encrypted = f.read()
        
        decrypted = self.cipher.decrypt(encrypted).decode()
        secrets = json.loads(decrypted)
        
        resolved_key = self._resolve_key(key)
        return secrets.get(resolved_key)
    
    def _set_secret_backend(self, key: str, value: str) -> None:
        # Load existing secrets
        secrets = {}
        if os.path.exists(self.secrets_file):
            with open(self.secrets_file, 'rb') as f:
                encrypted = f.read()
            decrypted = self.cipher.decrypt(encrypted).decode()
            secrets = json.loads(decrypted)
        
        # Add/update secret
        resolved_key = self._resolve_key(key)
        secrets[resolved_key] = value
        
        # Save encrypted
        encrypted = self.cipher.encrypt(json.dumps(secrets).encode())
        with open(self.secrets_file, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.secrets_file, 0o600)
    
    def _resolve_key(self, key: str) -> str:
        """Apply naming convention"""
        if self.config.naming_convention == "flat":
            return key
        elif self.config.naming_convention == "hierarchy":
            return f"{self.config.naming_prefix}/{self.config.naming_environment}/{key}"
        return key
    
    def get_plugin_name(self) -> str:
        return "local_file"
```

**Use case**: Single developer or small team, no external dependencies

**Setup**:
```bash
sc-conductor secrets init
# Creates ~/.sc-conductor/secrets.enc (encrypted)
# Creates ~/.sc-conductor/key.bin (local key)

sc-conductor secrets set jira_token "abc123"
sc-conductor secrets set slack_webhook "https://..."

# Test
sc-conductor run --all  # Reads from encrypted file
```

---

### 3.3 HashiCorp Vault Plugin

```python
import hvac

class VaultSecretsPlugin(SecretsPlugin):
    """Integrate with HashiCorp Vault"""
    
    def __init__(self, config: SecretsConfig):
        super().__init__(config)
        
        # Authenticate to Vault
        self.client = self._authenticate()
        self.secret_path = config.vault_namespace or "secret/data/sc-conductor"
    
    def _authenticate(self) -> hvac.Client:
        """Authenticate using configured method"""
        client = hvac.Client(url=self.config.vault_addr)
        
        if self.config.vault_auth_method == "token":
            # Token auth (for CI/CD)
            token = os.environ.get("VAULT_TOKEN")
            client.token = token
        
        elif self.config.vault_auth_method == "oidc":
            # OIDC auth (for users)
            response = client.auth.oidc.oidc_authorization_request_and_get_token(
                path="oidc"
            )
            client.token = response['auth']['client_token']
        
        elif self.config.vault_auth_method == "aws":
            # AWS IAM auth
            response = client.auth.aws.iam_login(
                access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
                secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                header_value=os.environ.get("VAULT_ADDR")
            )
            client.token = response['auth']['client_token']
        
        return client
    
    def _fetch_secret(self, key: str) -> Optional[str]:
        try:
            resolved_key = self._resolve_key(key)
            response = self.client.secrets.kv.v2.read_secret_version(
                path=resolved_key
            )
            return response['data']['data'].get('value')
        except Exception as e:
            self._log_audit("vault_read_failed", key, str(e), success=False)
            return None
    
    def _set_secret_backend(self, key: str, value: str) -> None:
        resolved_key = self._resolve_key(key)
        self.client.secrets.kv.v2.create_or_update_secret(
            path=resolved_key,
            secret_dict={'value': value}
        )
    
    def _resolve_key(self, key: str) -> str:
        """Apply naming convention for Vault hierarchy"""
        if self.config.naming_convention == "flat":
            return key
        elif self.config.naming_convention == "hierarchy":
            parts = [
                self.config.naming_prefix,
                self.config.naming_environment,
                key.replace('_', '/')
            ]
            return "/".join(parts)
        return key
    
    def get_plugin_name(self) -> str:
        return "vault"
```

**Use case**: Teams, enterprises with centralized secret management

**Setup**:
```bash
# Vault admin creates policy
vault policy write sc-conductor -<<EOF
path "secret/data/sc-conductor/prod/*" {
  capabilities = ["read", "create", "update"]
}
EOF

# User authenticates
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="$(vault login -method=oidc)"

# Framework uses it
sc-conductor run --all  # Reads from Vault
```

---

### 3.4 AWS Secrets Manager Plugin

```python
import boto3

class AwsSecretsPlugin(SecretsPlugin):
    """Integrate with AWS Secrets Manager"""
    
    def __init__(self, config: SecretsConfig):
        super().__init__(config)
        self.client = boto3.client(
            'secretsmanager',
            region_name=config.aws_region
        )
    
    def _fetch_secret(self, key: str) -> Optional[str]:
        try:
            resolved_key = self._resolve_key(key)
            response = self.client.get_secret_value(SecretId=resolved_key)
            return response.get('SecretString')
        except Exception:
            return None
    
    def _set_secret_backend(self, key: str, value: str) -> None:
        resolved_key = self._resolve_key(key)
        try:
            self.client.put_secret_value(
                SecretId=resolved_key,
                SecretString=value
            )
        except self.client.exceptions.ResourceNotFoundException:
            self.client.create_secret(
                Name=resolved_key,
                SecretString=value
            )
    
    def _resolve_key(self, key: str) -> str:
        """AWS naming: sc-conductor/prod/jira-token"""
        if self.config.naming_convention == "hierarchy":
            return f"{self.config.naming_prefix}/{self.config.naming_environment}/{key}"
        return key
    
    def get_plugin_name(self) -> str:
        return "aws_secrets_manager"
```

**Use case**: AWS-based deployments (Lambda, ECS, EC2)

---

## 4. Secrets Naming Convention

### Flat Convention
```
jira_token
slack_webhook
github_token
```

### Hierarchy Convention (Recommended)
```
sc-conductor/dev/jira/token
sc-conductor/dev/slack/webhook
sc-conductor/prod/jira/token
sc-conductor/prod/slack/webhook
```

### Custom Convention
```yaml
secrets_plugin:
  naming_convention: custom
  naming_pattern: "{prefix}_{environment}_{key}"
  # Results in: sc-conductor_prod_jira_token
```

---

## 5. Secret Rotation Strategy

### Manual Rotation

```bash
# Admin rotates secret
sc-conductor secrets rotate jira_token

# Process:
# 1. Generate new token (or accept from stdin)
# 2. Store new value in backend
# 3. Mark old value as deprecated
# 4. Apply grace_period_seconds (default 60s)
# 5. All systems get new value automatically (via cache invalidation)
# 6. After grace period, delete old value
# 7. Send notifications
```

### Scheduled Rotation

```yaml
secrets_plugin:
  rotation:
    schedule: "weekly"  # daily | weekly | monthly
    day: "sunday"
    time: "02:00 UTC"
    notify_on_rotation: true
```

### Graceful Transition

```
Timeline:

T=0s    Rotation initiated
        New secret: XXXX_NEW
        Old secret: XXXX (still active)

T=0-60s Grace period
        Systems can use either old or new
        Cache invalidated, systems fetch new

T=60s   Grace period expires
        Old secret deleted
        Only new secret valid

Notification: Sent at T=0 and T=60s
```

---

## 6. Audit and Compliance

### Audit Log Format

```json
[
  {
    "timestamp": "2026-10-07T10:30:00Z",
    "action": "read",
    "key": "jira_token",
    "details": "success",
    "user": "alice@company.com",
    "hostname": "localhost",
    "source": "secrets_plugin"
  },
  {
    "timestamp": "2026-10-07T10:31:00Z",
    "action": "rotate_start",
    "key": "jira_token",
    "user": "admin",
    "hostname": "vault-admin",
    "source": "secrets_plugin"
  },
  {
    "timestamp": "2026-10-07T10:32:00Z",
    "action": "rotate_complete",
    "key": "jira_token",
    "grace_period_seconds": 60,
    "user": "admin",
    "source": "secrets_plugin"
  }
]
```

### Immutable Log (SOC2 Compliance)

```yaml
secrets_plugin:
  audit:
    enabled: true
    retention_days: 2555  # 7 years
    immutable_log: true   # Append-only, no edits
    output_file: /var/log/sc-conductor/secrets-audit.json
```

### Retention Policy

```bash
# Auto-archive old logs
sc-conductor secrets audit --archive --before 2026-01-01
# Moves to: /var/log/sc-conductor/archive/secrets-audit-2025.json.gz
```

---

## 7. RBAC for Secrets

### Access Levels

```yaml
secrets_plugin:
  access_levels:
    developer:
      read_only: true
      can_rotate: false
      keys: ["*"]  # Can read any key
    
    ops_admin:
      read_only: false
      can_rotate: true
      keys: ["*"]
    
    security_admin:
      read_only: false
      can_rotate: true
      keys: ["*"]
      audit_access: true  # Can view audit logs
```

### Permission Checks

```python
def get_secret(self, key: str) -> Optional[str]:
    # Check RBAC
    if not self._has_permission("read", key):
        self._log_audit("denied_read", key, 
                       reason="insufficient_permissions")
        raise PermissionError(f"Cannot read {key}")
    
    # Proceed with retrieval...
```

---

## 8. Integration with Output Plugins

### Example: Jira Plugin Using Secrets

```python
class JiraOutputPlugin(OutputPlugin):
    def __init__(self, config: Dict, secrets_manager: SecretsManager):
        self.jira_url = config['url']
        self.jira_token = secrets_manager.get_secret('jira_token')
        # Token is never logged or exposed
    
    def push_test_failure(self, test_name: str, failure: Dict):
        jira = JIRA(self.jira_url, token_auth=self.jira_token)
        jira.create_issue(...)
        # Token used securely, never in logs
```

---

## 9. Migration Paths

### From Environment Variables to Local File

```bash
# Export current env vars
env | grep SC_CONDUCTOR_ > /tmp/secrets.env

# Migrate to local file
sc-conductor secrets migrate --from env --to local_file < /tmp/secrets.env

# Verify
sc-conductor secrets list
# ✓ All secrets now in ~/.sc-conductor/secrets.enc
```

### From Local File to Vault

```bash
# Migrate with verification
sc-conductor secrets migrate --from local_file --to vault \
  --vault-addr https://vault.company.com \
  --verify  # Test each secret after migration

# Verify
sc-conductor secrets list  # Now reading from Vault
```

---

## 10. Security Best Practices

### In Source Control

```bash
# .gitignore
.sc-conductor/
.conductor.local.yml

# Never commit:
# ~/.sc-conductor/key.bin (encryption key)
# ~/.sc-conductor/secrets.enc (encrypted secrets)
# Vault tokens
# AWS credentials
```

### Environment

```bash
# Secure environment variable passing
# BAD:
export VAULT_TOKEN="s.xxxxxxx"  # In shell history!

# GOOD:
export VAULT_TOKEN="$(vault login -method=oidc -format=json | jq -r '.auth.client_token')"
# Rotates immediately after use

# BETTER:
# Use OIDC/IAM auth, no long-lived tokens
```

### Logging

```python
# Good: Don't log secrets
logger.info(f"Using Jira token")

# Bad: Logs expose secrets!
logger.info(f"Jira token: {jira_token}")
```

### Rotation

```bash
# Good: Automatic monthly rotation
sc-conductor secrets rotate --schedule monthly

# Bad: Never rotate = compromised credentials persist
```

---

## Summary

| Aspect | Local Dev | Small Team | Enterprise |
|--------|-----------|-----------|-----------|
| **Backend** | env vars | local_file | vault |
| **Fallback** | none | env | fail |
| **Caching** | no | yes (300s) | yes (300s) |
| **Rotation** | manual | manual/scheduled | scheduled |
| **Audit** | no | yes (30d) | yes (7yr immutable) |
| **RBAC** | no | no | yes (admin/ops) |
| **Cost** | $0 | $0 | $5k/year |

**Recommendation**: Start with `env` or `local_file`, graduate to Vault when team grows or compliance required.
