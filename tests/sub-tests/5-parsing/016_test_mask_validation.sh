#!/bin/bash

#############################################################################
# GREPNET TEST: Subnet Mask and Hostmask Validation
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "SUBNET MASK AND HOSTMASK VALIDATION"

# Valid Subnet Masks (contiguous 1s from MSB, then 0s)

# SPEC: Valid subnet masks have contiguous 1-bits from MSB, representing network portion
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Valid subnet masks have contiguous 1-bits from MSB"
test_case "Valid subnet mask: 255.255.255.0 (/24)" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0 255.255.255.0'" 0 $'192.0.2.0' ""

# SPEC: /16 subnet mask 255.255.0.0 is valid and recognized
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Subnet masks must have MSB=1"
test_case "Valid subnet mask: 255.255.0.0 (/16)" \
    "echo '192.0.2.1' | $GREPNET '192.0.0.0 255.255.0.0'" 0 $'192.0.2.1' ""

# SPEC: /8 subnet mask 255.0.0.0 is valid and recognized
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Contiguous 1s represent network bits"
test_case "Valid subnet mask: 255.0.0.0 (/8)" \
    "echo '192.0.2.1' | $GREPNET '192.0.0.0 255.0.0.0'" 0 $'192.0.2.1' ""

# SPEC: /25 subnet mask 255.255.255.128 is valid (contiguous 1s + 1 zero)
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Validate contiguous 1-bits from MSB"
test_case "Valid subnet mask: 255.255.255.128 (/25)" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.0 255.255.255.128'" 0 $'192.0.2.1' ""

# SPEC: /32 subnet mask 255.255.255.255 represents a host mask (single IP)
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "All 1-bits = /32 host mask"
test_case "Valid subnet mask: 255.255.255.255 (/32 - host)" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.1 255.255.255.255'" 0 $'192.0.2.1' ""

# Invalid Subnet Masks (non-contiguous, should extract as plain IPs)

# SPEC: Non-contiguous masks (gaps in 1-bits) are invalid and extracted as two separate plain IPs
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Mask must have contiguous 1-bits from MSB; non-contiguous rejected"
test_case "Invalid subnet mask: 255.0.255.0 (non-contiguous) - extracts as two IPs" \
    "echo 'text 192.0.2.0 255.0.255.0 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 255.0.255.0 text' ""

# SPEC: Non-contiguous masks with gaps are invalid; extracted as two separate plain IPs
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Non-contiguous 1-bits are invalid"
test_case "Invalid subnet mask: 255.255.0.255 (non-contiguous) - extracts as two IPs" \
    "echo 'text 192.0.2.0 255.255.0.255 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 255.255.0.255 text' ""

# SPEC: Subnet masks must have MSB=1; if MSB=0, it's not a valid subnet mask
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Must have MSB=1 in first octet"
test_case "Invalid subnet mask: 0.255.255.255 (MSB is 0) - extracts as two IPs" \
    "echo 'text 192.0.2.0 0.255.255.255 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 0.255.255.255 text' ""

# Valid Hostmasks (contiguous 0s from MSB, then 1s)

# SPEC: Valid hostmasks have contiguous 0-bits from MSB, with all 1s in host portion
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Hostmask format has MSB=0 and contiguous 1s"
test_case "Valid hostmask: 0.0.0.255 (/24)" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0 0.0.0.255'" 0 $'192.0.2.0' ""

# SPEC: /16 hostmask 0.0.255.255 is valid (contiguous 0s then 1s)
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Contiguous 0s from MSB with all remaining 1s"
test_case "Valid hostmask: 0.0.255.255 (/16)" \
    "echo '192.0.2.1' | $GREPNET '192.0.0.0 0.0.255.255'" 0 $'192.0.2.1' ""

# SPEC: /8 hostmask 0.255.255.255 is valid (contiguous 0s with all 1s)
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Valid hostmasks have contiguous pattern"
test_case "Valid hostmask: 0.255.255.255 (/8)" \
    "echo '192.0.2.1' | $GREPNET '192.0.0.0 0.255.255.255'" 0 $'192.0.2.1' ""

# SPEC: /25 hostmask 0.0.0.127 is valid (MSB=0, contiguous 1s in lower bits)
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Hostmask with contiguous 1-bits pattern"
test_case "Valid hostmask: 0.0.0.127 (/25)" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.0 0.0.0.127'" 0 $'192.0.2.1' ""

# SPEC: /32 hostmask 0.0.0.0 represents a single host (all 0s means no host bits)
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "All 0-bits in hostmask = /32"
test_case "Valid hostmask: 0.0.0.0 (/32 - host)" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.1 0.0.0.0'" 0 $'192.0.2.1' ""

# Invalid Hostmasks (non-contiguous, should extract as plain IPs)

# SPEC: Non-contiguous hostmasks (gaps in 1-bits) are invalid and extracted as two separate IPs
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Hostmask must be contiguous"
test_case "Invalid hostmask: 0.255.0.255 (non-contiguous) - extracts as two IPs" \
    "echo 'text 192.0.2.0 0.255.0.255 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 0.255.0.255 text' ""

# SPEC: Hostmasks must have MSB=0; if MSB=1, try subnet mask parsing first, then reject if invalid
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "If MSB is 1, this is netmask format, not hostmask"
test_case "Invalid hostmask: 255.0.0.0 (MSB is 1) - try as subnet mask, fail, extract as IPs" \
    "echo 'text 192.0.2.0 255.0.0.0 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 255.0.0.0 text' ""

# SPEC: When MSB=1 and pattern is non-contiguous as subnet mask, reject both formats and extract as plain IPs
# SPEC-REF: GREPNET-SPEC.md - Parsing Strategy: "Non-contiguous rejected in both subnet and hostmask parsing"
test_case "Invalid hostmask: 255.255.255.0 (MSB is 1) - try as subnet mask, fail, extract as IPs" \
    "echo 'text 192.0.2.0 255.255.255.0 text' | $GREPNET '192.0.2.0'" 0 $'text 192.0.2.0 255.255.255.0 text' ""

# Coloring validation - only matched IP should be colored

# SPEC: Color output should only highlight the matched portion; non-contiguous masks extract as plain IP
# SPEC-REF: GREPNET-SPEC.md - Color Output: "Only matched networks are colored"
test_output_with_colors "Non-contiguous mask causes plain IP extraction - only 192.0.2.0 colored" \
    "echo 'text 192.0.2.0 255.0.255.0 text' | $GREPNET --color=always '192.0.2.0'" \
    0 \
    "text 192.0.2.0 255.0.255.0 text"

# SPEC: Valid subnet masks are recognized and colored as matched networks
# SPEC-REF: GREPNET-SPEC.md - Color Output: "Matched networks highlighted in color"
test_output_with_colors "Valid subnet mask - network colored as match" \
    "echo '192.0.2.0 255.255.255.0' | $GREPNET --color=always '192.0.2.0/24'" \
    0 \
    "192.0.2.0 255.255.255.0"

# Priority order: subnet mask should be tried before hostmask

# SPEC: When both subnet mask and hostmask are possible, subnet mask parsing takes priority
# SPEC-REF: GREPNET-SPEC.md - Parsing Strategy: "Subnet mask parsing before hostmask parsing"
test_case "Priority: 255.255.255.0 (valid subnet mask, MSB=1) not parsed as hostmask" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0 255.255.255.0'" 0 \
    $'192.0.2.0' ""

# SPEC: Hostmask format (MSB=0) is recognized and not confused with subnet mask format
# SPEC-REF: GREPNET-SPEC.md - Parsing Strategy: "Hostmask has MSB=0, distinguishing it from subnet mask"
test_case "Priority: 0.0.0.255 (valid hostmask, MSB=0) not parsed as subnet mask" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0 0.0.0.255'" 0 \
    $'192.0.2.0' ""

