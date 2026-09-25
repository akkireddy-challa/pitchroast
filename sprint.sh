#!/usr/bin/env bash
# ==============================================================================
# PitchRoast 🔥 - Hackathon Sprint Cockpit & Control Center
# For Stockholm Fable 5.1 x Opus 5.5 Build Day @ Epicenter
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

VENV_PYTHON="$DIR/.venv/bin/python"
VENV_STREAMLIT="$DIR/.venv/bin/streamlit"
VENV_RUFF="$DIR/.venv/bin/ruff"

# Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Header Banner
show_banner() {
    clear
    echo -e "${ORANGE}${BOLD}"
    echo "  ██████╗ ██╗████████╗ ██████╗██╗  ██╗██████╗  ██████╗  █████╗ ███████╗████████╗"
    echo "  ██╔══██╗██║╚══██╔══╝██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔══██╗██╔════╝╚══██╔══╝"
    echo "  ██████╔╝██║   ██║   ██║     ███████║██████╔╝██║   ██║███████║███████╗   ██║   "
    echo "  ██╔═══╝ ██║   ██║   ██║     ██╔══██║██╔══██╗██║   ██║██╔══██║╚════██║   ██║   "
    echo "  ██║     ██║   ██║   ╚██████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║   ██║   "
    echo "  ╚═╝     ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   "
    echo -e "${NC}"
    echo -e "${CYAN}  🔥 Autonomous Venture Syndicate • Stockholm Build Day @ Epicenter${NC}"
    echo -e "${BLUE}  ======================================================================${NC}"
    
    # Calculate Sprint Time Countdown (Demo is at 20:30)
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)
    CURRENT_TOTAL_MIN=$((10#$CURRENT_HOUR * 60 + 10#$CURRENT_MIN))
    TARGET_TOTAL_MIN=$((20 * 60 + 30)) # 20:30
    DIFF_MIN=$((TARGET_TOTAL_MIN - CURRENT_TOTAL_MIN))
    
    if [ $DIFF_MIN -gt 0 ]; then
        HOURS_LEFT=$((DIFF_MIN / 60))
        MINS_LEFT=$((DIFF_MIN % 60))
        echo -e "  ⏳ ${BOLD}Sprint Countdown:${NC} ${GREEN}${HOURS_LEFT}h ${MINS_LEFT}m remaining until 20:30 Demos!${NC}"
    else
        echo -e "  🚀 ${RED}${BOLD}STAGE TIME:${NC} Demo Session in progress!"
    fi
    echo -e "${BLUE}  ======================================================================${NC}\n"
}

# 1. Verification
cmd_verify() {
    echo -e "${CYAN}${BOLD}[1/3] Checking API Key & Public Endpoint...${NC}"
    if [ ! -f .env ]; then
        echo -e "${RED}❌ .env file missing! Run ./set_key.sh <key>${NC}"
        return 1
    fi
    source .env
    echo -e "  • Key: ${GREEN}${ANTHROPIC_API_KEY:0:15}...${ANTHROPIC_API_KEY: -6}${NC}"
    echo -e "  • Base URL: ${GREEN}$ANTHROPIC_BASE_URL${NC}"

    echo -e "\n${CYAN}${BOLD}[2/3] Testing Frontier Model Connectivity...${NC}"
    $VENV_PYTHON "$DIR/test_connection.py"

    echo -e "\n${CYAN}${BOLD}[3/3] Checking Git & Local Environment...${NC}"
    git status -s
    echo -e "\n${GREEN}✅ Everything verified and operational!${NC}"
}

# 2. Run App
cmd_app() {
    echo -e "${GREEN}${BOLD}🚀 Launching Streamlit UI with Arize Phoenix Tracing...${NC}"
    echo -e "${ORANGE}Opening at http://localhost:8501 (Traces at http://localhost:6006)${NC}\n"
    $VENV_STREAMLIT run app.py
}

# 3. Run Live CLI Demo
cmd_demo() {
    echo -e "${PURPLE}${BOLD}⚡ Running Full Boardroom Roast in Terminal...${NC}\n"
    $VENV_PYTHON "$DIR/run_demo.py"
}

# 4. Launch Claude Code Pair Programmer
cmd_claude() {
    echo -e "${CYAN}${BOLD}🤖 Launching Claude Code CLI Pair Programmer...${NC}"
    echo -e "${ORANGE}Isolated from company proxy • Direct to Anthropic API${NC}\n"
    "$DIR/claude_hackathon.sh"
}

# 5. Open Phoenix Observability
cmd_phoenix() {
    echo -e "${BLUE}${BOLD}🔭 Opening Arize Phoenix Observability Dashboard...${NC}"
    open "http://localhost:6006" 2>/dev/null || xdg-open "http://localhost:6006" 2>/dev/null || echo "Open http://localhost:6006 in your browser"
}

# 6. Lint, Verify, & Git Push
cmd_push() {
    echo -e "${CYAN}${BOLD}🧹 Step 1: Running Ruff Auto-Linter...${NC}"
    $VENV_RUFF check --fix --isolated .
    
    echo -e "\n${CYAN}${BOLD}📦 Step 2: Git Status...${NC}"
    git status -s

    echo -e "\n${ORANGE}${BOLD}Enter commit message (or press enter for default):${NC} "
    read -r commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="feat: sprint update $(date +%H:%M)"
    fi

    git add .
    git commit -m "$commit_msg"
    
    # Check if remote exists
    if git remote | grep -q 'origin'; then
        echo -e "\n${GREEN}🚀 Pushing to GitHub...${NC}"
        git push origin main || git push
    else
        echo -e "\n${ORANGE}⚠️ No remote 'origin' configured yet.${NC}"
        echo -e "To create and push to a new repo automatically, run:"
        echo -e "  ${BOLD}gh repo create pitchroast --public --source=. --remote=origin --push${NC}"
    fi
}

# Interactive Menu
cmd_menu() {
    show_banner
    echo -e "${BOLD}Select an action to execute:${NC}\n"
    echo -e "  ${GREEN}1)${NC} 🚀 Run Streamlit App      ${BLUE}(Interactive Web Boardroom :8501)${NC}"
    echo -e "  ${GREEN}2)${NC} ⚡ Run CLI Demo           ${BLUE}(Instant 4-Agent Roast & Term Sheet)${NC}"
    echo -e "  ${GREEN}3)${NC} 🤖 Claude Code Co-Pilot   ${BLUE}(Interactive CLI Pair Programmer)${NC}"
    echo -e "  ${GREEN}4)${NC} 🔭 Open Arize Phoenix     ${BLUE}(Tracing Dashboard :6006)${NC}"
    echo -e "  ${GREEN}5)${NC} 🔑 Verify Connectivity    ${BLUE}(Test Key & Model Availability)${NC}"
    echo -e "  ${GREEN}6)${NC} 🧹 Lint Code (Ruff)       ${BLUE}(Auto-fix formatting errors)${NC}"
    echo -e "  ${GREEN}7)${NC} 📦 Commit & Push Code     ${BLUE}(Clean Git Push to GitHub)${NC}"
    echo -e "  ${GREEN}q)${NC} Quit\n"
    read -p "Enter choice [1-7 or q]: " choice

    case "$choice" in
        1) cmd_app ;;
        2) cmd_demo ;;
        3) cmd_claude ;;
        4) cmd_phoenix ;;
        5) cmd_verify ;;
        6) $VENV_RUFF check --fix --isolated . ;;
        7) cmd_push ;;
        q|Q) echo -e "\n${ORANGE}Happy Hacking! Good luck on stage! 🔥${NC}\n"; exit 0 ;;
        *) echo -e "${RED}Invalid choice!${NC}"; sleep 1; cmd_menu ;;
    esac
}

# Command Router
case "$1" in
    verify|check-api)
        cmd_verify
        ;;
    app|run)
        cmd_app
        ;;
    demo)
        cmd_demo
        ;;
    claude|code)
        cmd_claude
        ;;
    phoenix|traces)
        cmd_phoenix
        ;;
    push)
        cmd_push
        ;;
    lint)
        $VENV_RUFF check --fix --isolated .
        ;;
    *)
        cmd_menu
        ;;
esac
