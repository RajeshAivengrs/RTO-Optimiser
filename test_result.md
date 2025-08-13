#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

## user_problem_statement: 
Complete the RTO Optimizer application development, focusing on database migration from MongoDB to Postgres as requested, and ensuring deployment stability. Key priorities: 1) Make application completely database-agnostic during startup, 2) Complete MongoDB to Postgres migration, 3) Enhance existing features and ML services.

## backend:
  - task: "Health Check API"
    implemented: true
    working: true
    file: "server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Health check endpoint already handles database unavailability gracefully"

  - task: "KPI Analytics API"
    implemented: true
    working: true
    file: "server.py" 
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "KPI endpoint returns demo data when database unavailable"

  - task: "Weekly Scorecard API"
    implemented: true
    working: true
    file: "server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Scorecard endpoint returns demo data when database unavailable"

  - task: "Order Webhook API"
    implemented: true
    working: true
    file: "server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
        - working: false
          agent: "main"
          comment: "Webhook endpoints may crash when database unavailable - needs graceful handling"
        - working: true
          agent: "testing"
          comment: "✅ TESTED: Order webhook endpoint works gracefully when database unavailable. Returns success response with demo mode message. Handles both valid and invalid data appropriately with proper validation errors."

  - task: "Courier Event Webhook API"
    implemented: true
    working: false
    file: "server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "Webhook endpoints may crash when database unavailable - needs graceful handling"

  - task: "NDR Resolution API"
    implemented: true
    working: false
    file: "server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "NDR resolution may crash when database unavailable - needs graceful handling"

  - task: "Seller Dashboard API"
    implemented: true
    working: false
    file: "seller_routes.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "Seller routes directly use collections without checking if database available"

  - task: "WhatsApp Integration API"
    implemented: true
    working: false
    file: "whatsapp_routes.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "WhatsApp routes may crash when database unavailable - needs graceful handling"

  - task: "Database Migration to Postgres"
    implemented: false
    working: false
    file: "TBD"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: false
          agent: "main"
          comment: "User explicitly requested Postgres migration but not yet implemented - still using MongoDB"

## frontend:
  - task: "Operations Dashboard"
    implemented: true
    working: true
    file: "App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Main dashboard working with graceful API failure handling and demo data fallbacks"

  - task: "Seller Portal"
    implemented: true
    working: false
    file: "SellerDashboard.js"
    stuck_count: 1
    priority: "medium" 
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "Seller dashboard may fail if backend seller APIs crash due to database issues"

  - task: "WhatsApp Integration UI"
    implemented: true
    working: false
    file: "WhatsAppIntegration.js"
    stuck_count: 1
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "WhatsApp UI may fail if backend WhatsApp APIs crash due to database issues"

## metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

## test_plan:
  current_focus:
    - "Make all backend APIs database-agnostic during startup"
    - "Database Migration to Postgres"
    - "Order Webhook API"
    - "Courier Event Webhook API" 
    - "NDR Resolution API"
  stuck_tasks:
    - "Database Migration to Postgres"
  test_all: false
  test_priority: "high_first"

## agent_communication:
    - agent: "main"
      message: "Starting Phase 1: Making application completely database-agnostic during startup. Current assessment shows basic graceful handling exists but webhook endpoints and seller/whatsapp routes need improvement. Will update all endpoints to handle database unavailability gracefully before proceeding with Postgres migration."