VERSION     := 0.1.0
PKG_NAME    := bee-pagoda
ARCH        := amd64
DEB_FILE    := dist/$(PKG_NAME)_$(VERSION)_$(ARCH).deb
INSTALL_DIR := /usr/share/$(PKG_NAME)
BIN_DIR     := /usr/bin

# Files to include in the package / system install
SUITE_FILES := \
  bee-pagoda \
  run_suite.sh \
  dashboard.sh \
  main.py \
  checks.py \
  config_loader.py \
  gpu_provider.py \
  plugins_loader.py \
  trend_store.py

SUITE_DIRS := \
  scripts \
  profiles \
  plugins \
  web \
  assets

.PHONY: all install uninstall deb dist clean help

all: deb

## ── Local install (no package manager) ────────────────────────────────────

install: ## Install bee-pagoda to $(INSTALL_DIR) and $(BIN_DIR)/bee-pagoda
	@echo "[install] Installing $(PKG_NAME) $(VERSION) to $(INSTALL_DIR)"
	@install -d "$(DESTDIR)$(INSTALL_DIR)"
	@for f in $(SUITE_FILES); do \
	  if [ -f "$$f" ]; then \
	    install -m 644 "$$f" "$(DESTDIR)$(INSTALL_DIR)/$$f"; \
	  fi; \
	done
	@install -m 755 bee-pagoda "$(DESTDIR)$(INSTALL_DIR)/bee-pagoda"
	@install -m 755 run_suite.sh "$(DESTDIR)$(INSTALL_DIR)/run_suite.sh"
	@install -m 755 dashboard.sh "$(DESTDIR)$(INSTALL_DIR)/dashboard.sh"
	@for d in $(SUITE_DIRS); do \
	  if [ -d "$$d" ]; then \
	    cp -r "$$d" "$(DESTDIR)$(INSTALL_DIR)/$$d"; \
	    find "$(DESTDIR)$(INSTALL_DIR)/$$d" -name "*.sh" -exec chmod 755 {} +; \
	    find "$(DESTDIR)$(INSTALL_DIR)/$$d" -name "*.py" -exec chmod 644 {} +; \
	  fi; \
	done
	@install -d "$(DESTDIR)$(BIN_DIR)"
	@ln -sf "$(INSTALL_DIR)/bee-pagoda" "$(DESTDIR)$(BIN_DIR)/$(PKG_NAME)"
	@echo "[install] Done. Run: bee-pagoda help"

uninstall: ## Remove bee-pagoda from $(INSTALL_DIR) and $(BIN_DIR)
	@echo "[uninstall] Removing $(PKG_NAME)"
	@rm -f "$(DESTDIR)$(BIN_DIR)/$(PKG_NAME)"
	@rm -rf "$(DESTDIR)$(INSTALL_DIR)"
	@echo "[uninstall] Done."

## ── Debian package ─────────────────────────────────────────────────────────

deb: dist ## Build the Debian .deb package → $(DEB_FILE)

dist: ## Build distributable artifacts under dist/
	@echo "[dist] Building $(DEB_FILE)"
	@mkdir -p dist
	@rm -rf /tmp/bee-pagoda-pkg
	@# Build package tree
	@PKGROOT=/tmp/bee-pagoda-pkg; \
	  SUITE_INSTALL="$$PKGROOT$(INSTALL_DIR)"; \
	  install -d "$$SUITE_INSTALL"; \
	  install -d "$$PKGROOT$(BIN_DIR)"; \
	  for f in $(SUITE_FILES); do \
	    [ -f "$$f" ] && install -m 644 "$$f" "$$SUITE_INSTALL/$$f"; \
	  done; \
	  install -m 755 bee-pagoda "$$SUITE_INSTALL/bee-pagoda"; \
	  install -m 755 run_suite.sh "$$SUITE_INSTALL/run_suite.sh"; \
	  install -m 755 dashboard.sh "$$SUITE_INSTALL/dashboard.sh"; \
	  for d in $(SUITE_DIRS); do \
	    if [ -d "$$d" ]; then \
	      cp -r "$$d" "$$SUITE_INSTALL/$$d"; \
	      find "$$SUITE_INSTALL/$$d" -name "*.sh" -exec chmod 755 {} + 2>/dev/null || true; \
	      find "$$SUITE_INSTALL/$$d" -name "*.py" -exec chmod 644 {} + 2>/dev/null || true; \
	    fi; \
	  done; \
	  ln -sf "$(INSTALL_DIR)/bee-pagoda" "$$PKGROOT$(BIN_DIR)/$(PKG_NAME)"; \
	  install -d "$$PKGROOT/DEBIAN"; \
	  cp packaging/debian/control "$$PKGROOT/DEBIAN/control"; \
	  cp packaging/debian/postinst "$$PKGROOT/DEBIAN/postinst"; \
	  cp packaging/debian/prerm "$$PKGROOT/DEBIAN/prerm"; \
	  chmod 755 "$$PKGROOT/DEBIAN/postinst" "$$PKGROOT/DEBIAN/prerm"; \
	  install -d "$$PKGROOT/usr/share/doc/$(PKG_NAME)"; \
	  cp packaging/debian/copyright "$$PKGROOT/usr/share/doc/$(PKG_NAME)/copyright"; \
	  gzip -9 -c packaging/debian/changelog > "$$PKGROOT/usr/share/doc/$(PKG_NAME)/changelog.Debian.gz"; \
	  dpkg-deb --build --root-owner-group "$$PKGROOT" "$(DEB_FILE)"
	@echo "[dist] Built: $(DEB_FILE)"
	@dpkg-deb --info "$(DEB_FILE)"

clean: ## Remove build artifacts
	@rm -rf /tmp/bee-pagoda-pkg dist/
	@echo "[clean] Done."

help: ## Show this help
	@echo "Bee Pagoda Benchmark — Makefile targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "Install via .deb:"
	@echo "  sudo dpkg -i $(DEB_FILE)"
	@echo ""
	@echo "Uninstall via dpkg:"
	@echo "  sudo dpkg -r $(PKG_NAME)"
