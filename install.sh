#!/usr/bin/env bash
set -euo pipefail

# ─── amazon-lyr installer ────────────────────────────────────────────────
# curl -sSL https://raw.githubusercontent.com/ishan-parihar/amazon-lyr/main/install.sh | bash
#
# Installs amazon-lyr globally using uv (preferred) or pip/pipx as fallback.
# ──────────────────────────────────────────────────────────────────────────

REPO="https://github.com/ishan-parihar/amazon-lyr.git"
BIN="amazon-lyr"
MIN_PYTHON_VERSION="3.11"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}▸${NC} $*"; }
warn()  { echo -e "${YELLOW}▸${NC} $*"; }
err()   { echo -e "${RED}▸${NC} $*" >&2; }
step()  { echo -e "${BLUE}▸${NC} $*"; }

check_python() {
    local py=""
    for cmd in python3 python3.13 python3.12 python3.11; do
        if command -v "$cmd" &>/dev/null; then
            if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
                py="$cmd"; break
            fi
        fi
    done
    if [[ -z "$py" ]]; then
        err "Python ${MIN_PYTHON_VERSION}+ not found. Install it first: https://www.python.org/downloads/"
        exit 1
    fi
    info "Found Python: $($py --version)"
}

install_with_uv() {
    step "Installing with uv (isolated tool environment)…"
    if ! command -v uv &>/dev/null; then
        warn "uv not found — installing…"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    uv tool install --force "git+${REPO}"
}

install_with_pip() {
    step "Falling back to pip --user install…"
    python3 -m pip install --user --upgrade "git+${REPO}" || {
        err "pip install failed."
        exit 1
    }
    warn "Ensure ~/.local/bin is on your PATH to use ${BIN}."
}

main() {
    echo ""
    step "Installing ${BIN} from ${REPO}"
    check_python

    if command -v "${BIN}" &>/dev/null; then
        warn "Existing installation found at $(command -v "${BIN}") — upgrading."
    fi

    if command -v pipx &>/dev/null && [[ -z "${FORCE_UV:-}" ]]; then
        step "Installing with pipx…"
        pipx install --force "git+${REPO}" || install_with_uv || install_with_pip
    else
        install_with_uv || install_with_pip
    fi

    echo ""
    if command -v "${BIN}" &>/dev/null; then
        info "✔ ${BIN} installed: $(command -v "${BIN}")"
        echo ""
        echo "  Get started:"
        echo "    ${BIN}                          # home view"
        echo "    ${BIN} login --browser chrome   # import cookies (one-time)"
        echo "    ${BIN} serve                    # start MCP server"
        echo ""
    else
        err "Installation finished but '${BIN}' is not on PATH. Open a new shell and retry."
        exit 1
    fi
}

main "$@"
