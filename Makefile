# =============================================================================
# Variables
# =============================================================================
GO_VERSION     := 1.21.5
BINARY_NAME    := docker-image-cleaner
PACKAGE_NAME   := bifer-docker-image-cleaner

# Timestamp version (recalculated each time)
VERSION        := $(shell date -u +%Y%m%d%H%M%S)
CWD            := $(shell pwd)
CONTAINER_ROOT := /go/src/docker-image-cleaner

# =============================================================================
# Phony targets
# =============================================================================
.PHONY: help check compile package test_package clean

# =============================================================================
# Help
# =============================================================================
help:
	@echo "Docker Image Cleaner Build System"
	@echo "=================================="
	@echo ""
	@echo "Available targets:"
	@echo "  check          - Run linters (fmt, vet, staticcheck)"
	@echo "  compile        - Build binary (depends on check)"
	@echo "  package        - Create .deb package (depends on compile)"
	@echo "  test_package   - Test .deb installation"
	@echo "  clean          - Remove build artifacts"
	@echo ""
	@echo "Variables:"
	@echo "  GO_VERSION     - Go version (default: $(GO_VERSION))"
	@echo "  VERSION        - Package version (default: timestamp)"

# =============================================================================
# Code quality checks
# =============================================================================
check: $(BINARY_NAME).go go.mod go.sum
	sudo docker run --rm -v $(CWD):$(CONTAINER_ROOT) -w $(CONTAINER_ROOT) \
		golang:$(GO_VERSION) bash -c '\
		go fmt $(BINARY_NAME).go && \
		go vet $(BINARY_NAME).go && \
		go install honnef.co/go/tools/cmd/staticcheck@v0.4.7 && \
		staticcheck $(BINARY_NAME).go'

# =============================================================================
# Compile - depends on check to avoid duplicate work
# =============================================================================
compile: check
	sudo docker run --rm -v $(CWD):$(CONTAINER_ROOT) -w $(CONTAINER_ROOT) \
		golang:$(GO_VERSION) bash -c '\
		go mod tidy && \
		CGO_ENABLED=0 go build -ldflags="-s -w" -o $(BINARY_NAME) $(BINARY_NAME).go'

# =============================================================================
# Package (deb)
# =============================================================================
package: compile
	sudo docker build --build-arg GO_VERSION=$(GO_VERSION) --build-arg VERSION=$(VERSION) -o . .

# =============================================================================
# Test package installation
# =============================================================================
test_package: package
	sudo docker run --rm -v $(CWD):/stuff:ro debian:bookworm-slim \
		bash -c 'dpkg -i /stuff/$(PACKAGE_NAME)_*.deb'

# =============================================================================
# Clean
# =============================================================================
clean:
	rm -f $(BINARY_NAME) $(PACKAGE_NAME)_*.deb