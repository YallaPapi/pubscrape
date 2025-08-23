#!/bin/bash

# Test Runner Script for Pubscrape Testing Framework
# Executes comprehensive test suite with coverage reporting and CI/CD integration

set -e  # Exit on any error

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)"
TEST_DIR="$PROJECT_ROOT/tests"
COVERAGE_DIR="$PROJECT_ROOT/coverage"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
LOGS_DIR="$PROJECT_ROOT/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_SUITE]

Test runner for the Pubscrape testing framework.

TEST_SUITES:
    unit                Run unit tests only
    integration         Run integration tests only
    performance         Run performance benchmarks
    quality             Run data quality tests
    antidetection       Run anti-detection tests
    all                 Run all test suites (default)
    smoke               Run smoke tests (quick validation)
    regression          Run regression test suite

OPTIONS:
    -h, --help          Show this help message
    -v, --verbose       Verbose output
    -c, --coverage      Generate coverage report
    -r, --report        Generate test reports
    -f, --fail-fast     Stop on first failure
    -p, --parallel      Run tests in parallel
    -m, --markers       Specify pytest markers (e.g., "not slow")
    -e, --env           Set environment (dev, staging, prod)
    --html-report       Generate HTML test report
    --junit-xml         Generate JUnit XML report
    --clean             Clean previous test artifacts
    --install-deps      Install test dependencies
    --setup-env         Setup test environment
    --ci                CI/CD mode (non-interactive)

Examples:
    $0 unit -c                          # Run unit tests with coverage
    $0 integration --html-report        # Run integration tests with HTML report
    $0 all -p -r                        # Run all tests in parallel with reports
    $0 smoke --ci                       # Run smoke tests in CI mode
    $0 performance -m "not slow"        # Run performance tests excluding slow ones

EOF
}

# Default values
TEST_SUITE="all"
VERBOSE=false
COVERAGE=false
REPORT=false
FAIL_FAST=false
PARALLEL=false
MARKERS=""
ENVIRONMENT="dev"
HTML_REPORT=false
JUNIT_XML=false
CLEAN=false
INSTALL_DEPS=false
SETUP_ENV=false
CI_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -r|--report)
            REPORT=true
            shift
            ;;
        -f|--fail-fast)
            FAIL_FAST=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --html-report)
            HTML_REPORT=true
            shift
            ;;
        --junit-xml)
            JUNIT_XML=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --install-deps)
            INSTALL_DEPS=true
            shift
            ;;
        --setup-env)
            SETUP_ENV=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        unit|integration|performance|quality|antidetection|all|smoke|regression)
            TEST_SUITE="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Setup functions
setup_directories() {
    log_info "Setting up test directories..."
    mkdir -p "$COVERAGE_DIR" "$REPORTS_DIR" "$LOGS_DIR"
    
    # Create subdirectories for different report types
    mkdir -p "$REPORTS_DIR/html" "$REPORTS_DIR/xml" "$REPORTS_DIR/json"
}

clean_artifacts() {
    if [[ "$CLEAN" == "true" ]]; then
        log_info "Cleaning previous test artifacts..."
        rm -rf "$COVERAGE_DIR"/* "$REPORTS_DIR"/* "$LOGS_DIR"/*
        find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
        find "$PROJECT_ROOT" -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    fi
}

install_dependencies() {
    if [[ "$INSTALL_DEPS" == "true" ]]; then
        log_info "Installing test dependencies..."
        
        # Install main requirements
        pip install -r "$PROJECT_ROOT/requirements.txt"
        
        # Install additional test dependencies
        pip install pytest pytest-cov pytest-html pytest-xdist pytest-mock pytest-asyncio
        pip install coverage[toml] pytest-benchmark pytest-timeout
        pip install email-validator beautifulsoup4 pandas numpy
        
        log_success "Dependencies installed successfully"
    fi
}

setup_environment() {
    if [[ "$SETUP_ENV" == "true" ]]; then
        log_info "Setting up test environment..."
        
        # Set environment variables
        export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
        export TEST_ENVIRONMENT="$ENVIRONMENT"
        export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
        
        # Create test configuration file
        cat > "$PROJECT_ROOT/pytest.ini" << EOF
[tool:pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    quality: Data quality tests
    antidetection: Anti-detection tests
    slow: Slow running tests
    browser: Tests requiring browser
    network: Tests requiring network access
EOF
        
        log_success "Test environment configured"
    fi
}

# Test execution functions
build_pytest_command() {
    local test_path="$1"
    local cmd="python -m pytest"
    
    # Add test path
    cmd="$cmd $test_path"
    
    # Add verbose output
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v -s"
    fi
    
    # Add fail fast
    if [[ "$FAIL_FAST" == "true" ]]; then
        cmd="$cmd -x"
    fi
    
    # Add parallel execution
    if [[ "$PARALLEL" == "true" ]]; then
        cmd="$cmd -n auto"
    fi
    
    # Add markers
    if [[ -n "$MARKERS" ]]; then
        cmd="$cmd -m \"$MARKERS\""
    fi
    
    # Add coverage
    if [[ "$COVERAGE" == "true" ]]; then
        cmd="$cmd --cov=src --cov-report=html:$COVERAGE_DIR/html --cov-report=xml:$COVERAGE_DIR/coverage.xml --cov-report=term"
    fi
    
    # Add HTML report
    if [[ "$HTML_REPORT" == "true" ]]; then
        cmd="$cmd --html=$REPORTS_DIR/html/report.html --self-contained-html"
    fi
    
    # Add JUnit XML
    if [[ "$JUNIT_XML" == "true" ]]; then
        cmd="$cmd --junit-xml=$REPORTS_DIR/xml/junit.xml"
    fi
    
    # Add timeout for CI
    if [[ "$CI_MODE" == "true" ]]; then
        cmd="$cmd --timeout=300"
    fi
    
    echo "$cmd"
}

run_test_suite() {
    local suite="$1"
    local start_time=$(date +%s)
    
    log_info "Running $suite tests..."
    
    case "$suite" in
        "unit")
            cmd=$(build_pytest_command "$TEST_DIR/unit")
            ;;
        "integration")
            cmd=$(build_pytest_command "$TEST_DIR/integration")
            ;;
        "performance")
            cmd=$(build_pytest_command "$TEST_DIR/performance")
            ;;
        "quality")
            cmd=$(build_pytest_command "$TEST_DIR/quality")
            ;;
        "antidetection")
            cmd=$(build_pytest_command "$TEST_DIR -m antidetection")
            ;;
        "smoke")
            cmd=$(build_pytest_command "$TEST_DIR -m 'not slow and not performance'")
            ;;
        "regression")
            cmd=$(build_pytest_command "$TEST_DIR -m 'not antidetection'")
            ;;
        "all")
            cmd=$(build_pytest_command "$TEST_DIR")
            ;;
        *)
            log_error "Unknown test suite: $suite"
            exit 1
            ;;
    esac
    
    # Execute the command
    log_info "Executing: $cmd"
    
    if eval "$cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "$suite tests completed successfully in ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_error "$suite tests failed after ${duration}s"
        return 1
    fi
}

# Coverage analysis
analyze_coverage() {
    if [[ "$COVERAGE" == "true" ]]; then
        log_info "Analyzing test coverage..."
        
        # Generate coverage report
        cd "$PROJECT_ROOT"
        python -m coverage report --show-missing
        
        # Check coverage thresholds
        local coverage_percent=$(python -m coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
        
        if [[ -n "$coverage_percent" ]]; then
            log_info "Overall coverage: ${coverage_percent}%"
            
            if (( $(echo "$coverage_percent >= 80" | bc -l) )); then
                log_success "Coverage meets minimum threshold (80%)"
            else
                log_warning "Coverage below minimum threshold (80%): ${coverage_percent}%"
            fi
        fi
        
        # Generate coverage badge (if in CI)
        if [[ "$CI_MODE" == "true" ]]; then
            echo "COVERAGE_PERCENT=$coverage_percent" >> "$REPORTS_DIR/coverage.env"
        fi
    fi
}

# Test report generation
generate_reports() {
    if [[ "$REPORT" == "true" ]] || [[ "$HTML_REPORT" == "true" ]] || [[ "$JUNIT_XML" == "true" ]]; then
        log_info "Generating test reports..."
        
        # Create summary report
        cat > "$REPORTS_DIR/test_summary.json" << EOF
{
    "test_suite": "$TEST_SUITE",
    "environment": "$ENVIRONMENT",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "configuration": {
        "verbose": $VERBOSE,
        "coverage": $COVERAGE,
        "parallel": $PARALLEL,
        "markers": "$MARKERS"
    }
}
EOF
        
        # List generated reports
        log_info "Test reports generated in: $REPORTS_DIR"
        find "$REPORTS_DIR" -type f -name "*.html" -o -name "*.xml" -o -name "*.json" | sort
    fi
}

# Quality gates
check_quality_gates() {
    local exit_code=0
    
    log_info "Checking quality gates..."
    
    # Check if critical tests passed
    if [[ "$TEST_SUITE" == "all" ]] || [[ "$TEST_SUITE" == "unit" ]]; then
        # Unit tests are critical
        if ! run_test_suite "unit" > /dev/null 2>&1; then
            log_error "Quality gate failed: Unit tests must pass"
            exit_code=1
        fi
    fi
    
    # Check coverage threshold
    if [[ "$COVERAGE" == "true" ]]; then
        local coverage_file="$COVERAGE_DIR/coverage.xml"
        if [[ -f "$coverage_file" ]]; then
            local coverage_percent=$(grep -o 'line-rate="[^"]*"' "$coverage_file" | head -1 | cut -d'"' -f2 | awk '{print $1 * 100}')
            if (( $(echo "$coverage_percent < 70" | bc -l) )); then
                log_error "Quality gate failed: Coverage too low (${coverage_percent}% < 70%)"
                exit_code=1
            fi
        fi
    fi
    
    return $exit_code
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    log_info "Starting test execution for suite: $TEST_SUITE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Configuration: verbose=$VERBOSE, coverage=$COVERAGE, parallel=$PARALLEL"
    
    # Setup
    setup_directories
    clean_artifacts
    install_dependencies
    setup_environment
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run pre-flight checks
    if ! python -c "import sys; print(f'Python {sys.version}')"; then
        log_error "Python is not available"
        exit 1
    fi
    
    if ! python -c "import pytest; print(f'pytest {pytest.__version__}')"; then
        log_error "pytest is not available"
        exit 1
    fi
    
    # Execute tests
    local test_exit_code=0
    
    if ! run_test_suite "$TEST_SUITE"; then
        test_exit_code=1
    fi
    
    # Post-test analysis
    analyze_coverage
    generate_reports
    
    # Quality gates (only in CI mode)
    if [[ "$CI_MODE" == "true" ]]; then
        if ! check_quality_gates; then
            test_exit_code=1
        fi
    fi
    
    # Summary
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    if [[ $test_exit_code -eq 0 ]]; then
        log_success "All tests completed successfully in ${total_duration}s"
        
        if [[ "$COVERAGE" == "true" ]]; then
            log_info "Coverage report available at: $COVERAGE_DIR/html/index.html"
        fi
        
        if [[ "$HTML_REPORT" == "true" ]]; then
            log_info "HTML report available at: $REPORTS_DIR/html/report.html"
        fi
    else
        log_error "Tests failed after ${total_duration}s"
        
        if [[ "$CI_MODE" == "true" ]]; then
            log_info "Check the test reports for detailed failure information"
        fi
    fi
    
    exit $test_exit_code
}

# Trap signals for cleanup
trap 'log_warning "Test execution interrupted"; exit 130' INT TERM

# Run main function
main "$@"
