#!/bin/bash

# AMC-trader Worktree Setup Script
# Creates isolated git worktrees for parallel Claude development sessions

set -e  # Exit on error

echo "=========================================="
echo "AMC-trader Git Worktree Setup"
echo "=========================================="

# Configuration
REPO_URL="https://github.com/mikedmote52/AMC-trader.git"
PROJECT_DIR="$HOME/projects"
REPO_NAME="AMC-trader"
SESSIONS_DIR="AMC-sessions"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 0: Create projects directory if it doesn't exist
echo -e "${YELLOW}Step 0: Setting up project directory...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Step 1: Clone the repository if it doesn't exist
if [ ! -d "$REPO_NAME" ]; then
    echo -e "${YELLOW}Step 1: Cloning repository...${NC}"
    git clone "$REPO_URL" "$REPO_NAME"
    cd "$REPO_NAME"
    
    # Make initial commit if repo is empty
    if [ -z "$(git log --oneline -1 2>/dev/null)" ]; then
        echo -e "${YELLOW}Creating initial commit for empty repo...${NC}"
        git commit --allow-empty -m "init: Repository initialization"
        git push -u origin main
    fi
else
    echo -e "${GREEN}Repository already exists, skipping clone...${NC}"
    cd "$REPO_NAME"
    
    # Fetch latest changes
    echo -e "${YELLOW}Fetching latest changes...${NC}"
    git fetch origin
fi

# Step 2: Create container folder for worktrees
echo -e "${YELLOW}Step 2: Creating worktree container directory...${NC}"
mkdir -p "../$SESSIONS_DIR"

# Step 3: Create isolated worktrees
echo -e "${YELLOW}Step 3: Creating isolated worktrees...${NC}"

# Array of worktrees to create
declare -a WORKTREES=(
    "AMC-api:api:API and backend services"
    "AMC-discovery:discovery:Stock discovery pipeline"
    "AMC-frontend:frontend-work:React frontend"
    "AMC-infra:infra-work:Infrastructure and deployment"
    "AMC-qa:qa:Testing and quality assurance"
)

# Function to create or update worktree
create_worktree() {
    local dir_name=$1
    local branch_name=$2
    local description=$3
    local worktree_path="../$SESSIONS_DIR/$dir_name"
    
    # Check if worktree already exists
    if git worktree list | grep -q "$worktree_path"; then
        echo -e "${GREEN}  ✓ Worktree '$dir_name' already exists${NC}"
    else
        # Check if branch exists on remote
        if git ls-remote --heads origin "$branch_name" | grep -q "$branch_name"; then
            echo -e "${YELLOW}  Creating worktree '$dir_name' from existing branch '$branch_name'...${NC}"
            git worktree add "$worktree_path" "$branch_name"
        else
            echo -e "${YELLOW}  Creating worktree '$dir_name' with new branch '$branch_name'...${NC}"
            git worktree add "$worktree_path" -b "$branch_name"
        fi
        echo -e "${GREEN}  ✓ Created: $description${NC}"
    fi
}

# Create each worktree
for worktree in "${WORKTREES[@]}"; do
    IFS=':' read -r dir_name branch_name description <<< "$worktree"
    create_worktree "$dir_name" "$branch_name" "$description"
done

# Step 4: Verify worktrees
echo -e "\n${YELLOW}Step 4: Verifying worktree setup...${NC}"
echo -e "${GREEN}Current worktrees:${NC}"
git worktree list

# Step 5: Create README in each worktree
echo -e "\n${YELLOW}Step 5: Initializing worktree READMEs...${NC}"

for worktree in "${WORKTREES[@]}"; do
    IFS=':' read -r dir_name branch_name description <<< "$worktree"
    worktree_path="../$SESSIONS_DIR/$dir_name"
    readme_path="$worktree_path/README.md"
    
    if [ ! -f "$readme_path" ]; then
        cat > "$readme_path" << EOF
# $dir_name

Branch: \`$branch_name\`
Purpose: $description

## Overview

This worktree is dedicated to: $description

## Development Guidelines

- Each Claude session should work in its designated worktree
- Commit frequently with descriptive messages
- Push changes regularly to the remote branch
- Coordinate merges through the main branch

## Quick Commands

\`\`\`bash
# Check current branch
git branch --show-current

# Stage and commit changes
git add .
git commit -m "feat: your descriptive message"

# Push to remote
git push origin $branch_name

# Pull latest changes
git pull origin $branch_name

# Switch back to this worktree from anywhere
cd $PROJECT_DIR/$SESSIONS_DIR/$dir_name
\`\`\`

## Integration

To merge changes from this branch to main:
\`\`\`bash
cd $PROJECT_DIR/$REPO_NAME
git checkout main
git merge $branch_name
git push origin main
\`\`\`
EOF
        echo -e "${GREEN}  ✓ Created README for $dir_name${NC}"
    else
        echo -e "${GREEN}  ✓ README already exists for $dir_name${NC}"
    fi
done

# Step 6: Create a master control script
echo -e "\n${YELLOW}Step 6: Creating master control script...${NC}"

CONTROL_SCRIPT="$PROJECT_DIR/$SESSIONS_DIR/control.sh"
cat > "$CONTROL_SCRIPT" << 'EOF'
#!/bin/bash

# AMC-trader Worktree Control Script

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_menu() {
    echo -e "\n${BLUE}=========================================="
    echo -e "AMC-trader Worktree Control Panel"
    echo -e "==========================================${NC}\n"
    echo "1) Show all worktrees status"
    echo "2) Pull all branches"
    echo "3) Push all branches"
    echo "4) Show recent commits across all branches"
    echo "5) Switch to worktree"
    echo "6) Clean merged branches"
    echo "q) Quit"
    echo
    read -p "Select option: " choice
}

show_status() {
    echo -e "\n${YELLOW}Worktree Status:${NC}"
    cd ../AMC-trader
    git worktree list
    echo
    for dir in AMC-api AMC-discovery AMC-frontend AMC-infra AMC-qa; do
        if [ -d "../AMC-sessions/$dir" ]; then
            echo -e "${GREEN}$dir:${NC}"
            cd "../AMC-sessions/$dir"
            git status -sb
            echo
        fi
    done
}

pull_all() {
    echo -e "\n${YELLOW}Pulling all branches...${NC}"
    for dir in AMC-api AMC-discovery AMC-frontend AMC-infra AMC-qa; do
        if [ -d "$dir" ]; then
            echo -e "${GREEN}Pulling $dir...${NC}"
            cd "$dir"
            git pull
            cd ..
        fi
    done
}

push_all() {
    echo -e "\n${YELLOW}Pushing all branches...${NC}"
    for dir in AMC-api AMC-discovery AMC-frontend AMC-infra AMC-qa; do
        if [ -d "$dir" ]; then
            echo -e "${GREEN}Pushing $dir...${NC}"
            cd "$dir"
            branch=$(git branch --show-current)
            git push origin "$branch"
            cd ..
        fi
    done
}

show_commits() {
    echo -e "\n${YELLOW}Recent commits (last 5 per branch):${NC}"
    cd ../AMC-trader
    for branch in api discovery frontend-work infra-work qa main; do
        echo -e "\n${GREEN}Branch: $branch${NC}"
        git log "$branch" --oneline -5 2>/dev/null || echo "  No commits yet"
    done
}

switch_worktree() {
    echo -e "\n${YELLOW}Available worktrees:${NC}"
    echo "1) AMC-api"
    echo "2) AMC-discovery"
    echo "3) AMC-frontend"
    echo "4) AMC-infra"
    echo "5) AMC-qa"
    read -p "Select worktree: " wt_choice
    
    case $wt_choice in
        1) cd AMC-api && exec bash ;;
        2) cd AMC-discovery && exec bash ;;
        3) cd AMC-frontend && exec bash ;;
        4) cd AMC-infra && exec bash ;;
        5) cd AMC-qa && exec bash ;;
        *) echo "Invalid choice" ;;
    esac
}

# Main loop
while true; do
    show_menu
    case $choice in
        1) show_status ;;
        2) pull_all ;;
        3) push_all ;;
        4) show_commits ;;
        5) switch_worktree ;;
        6) echo "Not implemented yet" ;;
        q) exit 0 ;;
        *) echo "Invalid option" ;;
    esac
done
EOF

chmod +x "$CONTROL_SCRIPT"
echo -e "${GREEN}✓ Created control script at: $CONTROL_SCRIPT${NC}"

# Step 7: Summary
echo -e "\n${GREEN}=========================================="
echo -e "✓ Setup Complete!"
echo -e "==========================================${NC}\n"

echo "Worktree Structure:"
echo "  $PROJECT_DIR/"
echo "    ├── $REPO_NAME/          (main repository)"
echo "    └── $SESSIONS_DIR/"
echo "        ├── AMC-api/         (api branch)"
echo "        ├── AMC-discovery/   (discovery branch)"
echo "        ├── AMC-frontend/    (frontend-work branch)"
echo "        ├── AMC-infra/       (infra-work branch)"
echo "        ├── AMC-qa/          (qa branch)"
echo "        └── control.sh       (management script)"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Each Claude session should work in its designated worktree"
echo "2. Navigate to a worktree: cd $PROJECT_DIR/$SESSIONS_DIR/AMC-api"
echo "3. Use control script: $CONTROL_SCRIPT"
echo "4. Start development in any worktree!"

echo -e "\n${GREEN}Happy coding! 🚀${NC}"