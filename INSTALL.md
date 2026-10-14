# Installation Guide

GrepNet can be installed as a standalone tool with man page support. This guide covers user-level installation to `~/bin` and `~/man`.

## Prerequisites

- Python 3.8 or later
- Bash shell
- Standard Unix utilities (mkdir, cp)

## Installation Steps

### 1. Create Installation Directories

```bash
mkdir -p ~/bin ~/man/man1
```

### 2. Update Your Shell Configuration

Add the following lines to your `~/.bashrc` to ensure `~/bin` and `~/man` are in your PATH and MANPATH:

#### Add ~/bin to PATH

```bash
if [[ ! "$PATH" =~ ":$HOME/bin" ]]; then 
  export PATH=$PATH:~/bin 
fi
```

Add this to `~/.bashrc`:

```bash
echo 'if [[ ! "$PATH" =~ ":$HOME/bin" ]]; then export PATH=$PATH:~/bin ; fi' >> ~/.bashrc
```

#### Add ~/man to MANPATH

```bash
if [[ ! $(manpath -q) =~ ":$HOME/man" ]]; then 
  export MANPATH=$(manpath -q):~/man 
fi
```

Add this to `~/.bashrc`:

```bash
echo 'if [[ ! $(manpath -q) =~ ":$HOME/man" ]]; then export MANPATH=$(manpath -q):~/man ; fi' >> ~/.bashrc
```

### 3. Reload Your Shell Configuration

```bash
source ~/.bashrc
```

### 4. Install GrepNet

Copy the compiled executable and man page to their respective directories:

```bash
cp grepnet ~/bin/
cp grepnet.1 ~/man/man1/
```

### 5. Verify Installation

Test that grepnet is accessible and properly installed:

```bash
# Test executable
grepnet --version

# Test man page
man grepnet
```

## Uninstallation

To remove GrepNet:

```bash
rm ~/bin/grepnet ~/man/man1/grepnet.1
```

## Troubleshooting

### Command Not Found

If `grepnet` command is not found:

1. Verify `~/bin` is in your PATH:
   ```bash
   echo $PATH
   ```
   Should include `/home/<username>/bin`

2. Reload your shell configuration:
   ```bash
   source ~/.bashrc
   ```

3. Verify the executable exists and is executable:
   ```bash
   ls -l ~/bin/grepnet
   ```

### Man Page Not Found

If `man grepnet` returns "No manual entry":

1. Verify `~/man` is in your MANPATH:
   ```bash
   manpath -q
   ```
   Should include `/home/<username>/man`

2. Reload your shell configuration:
   ```bash
   source ~/.bashrc
   ```

3. Verify the man page exists:
   ```bash
   ls -l ~/man/man1/grepnet.1
   ```

## Notes

- This installation method installs GrepNet for the current user only
- The executable must be in a directory listed in your PATH environment variable
- The man page must be in a directory listed in your MANPATH environment variable
- For system-wide installation, place files in standard system directories (requires sudo):
  - Binary: `/usr/local/bin/grepnet`
  - Man page: `/usr/local/man/man1/grepnet.1` or `/usr/share/man/man1/grepnet.1`
