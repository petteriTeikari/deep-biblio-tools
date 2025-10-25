# tex2lyx Docker Configuration Plan

## Problem Statement

tex2lyx fails in Docker containers with the error "tex2lyx: User directory does not exist" even when we create a temporary HOME directory with a `.lyx` subdirectory. This prevents the tex-to-lyx conversion functionality from working in containerized environments.

## Root Cause Analysis

1. **tex2lyx Requirements**: tex2lyx expects a fully configured LyX user directory with:
   - Configuration files
   - Layout definitions
   - User preferences
   - Possibly system-wide LyX installation paths

2. **Current Docker Environment**: Our minimal Docker image only installs the `lyx` package but doesn't initialize the user configuration.

## Proposed Solution

### Option 1: Initialize LyX User Directory (Recommended)

1. **Add LyX initialization to Dockerfile**:
   ```dockerfile
   # After installing lyx
   RUN apt-get update && apt-get install -y \
       git \
       curl \
       pandoc \
       lyx \
       && rm -rf /var/lib/apt/lists/* \
       && mkdir -p /root/.lyx \
       && lyx -batch -x reconfigure 2>/dev/null || true
   ```

2. **Create minimal LyX preferences**:
   ```dockerfile
   # Create minimal preferences file
   RUN echo '# LyX user preferences\n\
   \\format "lyx" "lyx" "LyX" "" "" "" "" ""\n\
   \\converter "tex" "lyx" "tex2lyx -f $$i $$o" ""' > /root/.lyx/preferences
   ```

3. **Copy system layouts to user directory**:
   ```dockerfile
   # Copy system layouts to user directory
   RUN cp -r /usr/share/lyx/layouts /root/.lyx/ || true
   ```

### Option 2: Use LyX's Built-in Configuration

1. **Run LyX configuration during Docker build**:
   ```dockerfile
   # Configure LyX properly
   RUN mkdir -p /root/.lyx && \
       yes '' | lyx -userdir /root/.lyx -x reconfigure || true
   ```

2. **Set environment variables**:
   ```dockerfile
   ENV LYX_USERDIR=/root/.lyx
   ENV HOME=/root
   ```

### Option 3: Minimal tex2lyx Configuration

1. **Create only what tex2lyx needs**:
   ```dockerfile
   # Create minimal tex2lyx configuration
   RUN mkdir -p /root/.lyx/layouts && \
       echo "Format 66" > /root/.lyx/lyxrc.defaults && \
       echo "\\tex_expects_windows_paths false" >> /root/.lyx/lyxrc.defaults
   ```

## Implementation Steps

1. **Remove the hacky workaround** from `tex_to_lyx.py`:
   - Remove the temporary HOME directory creation
   - Keep the CONTAINER_ENV check only for test skipping if needed

2. **Update Dockerfiles**:
   - `Dockerfile.test`: Add LyX configuration steps
   - `Dockerfile`: Add the same configuration for production image

3. **Test the solution**:
   - Build the Docker image locally
   - Run tex2lyx tests inside the container
   - Verify all tex2lyx functionality works

4. **Update test configuration**:
   - Remove the CONTAINER_ENV skip condition from tests
   - Ensure tests run in CI/CD pipeline

## Alternative Approaches

### Use tex2lyx standalone mode
Research if tex2lyx can run without full LyX configuration by:
- Using command-line flags to bypass user directory checks
- Setting specific environment variables
- Using minimal configuration mode

### Package pre-configured LyX directory
Create a minimal `.lyx` directory structure and package it with the Docker image:
```dockerfile
COPY docker/lyx-config /root/.lyx
```

## Testing Plan

1. **Local Docker testing**:
   ```bash
   docker build -f Dockerfile.test -t deep-biblio-test .
   docker run --rm deep-biblio-test bash -c "tex2lyx --version"
   docker run --rm deep-biblio-test bash -c "echo '\\documentclass{article}\\begin{document}Test\\end{document}' > test.tex && tex2lyx test.tex test.lyx && cat test.lyx"
   ```

2. **Run full test suite**:
   ```bash
   docker run --rm deep-biblio-test uv run pytest tests/converters/test_to_lyx.py -v
   ```

3. **CI/CD validation**:
   - Ensure GitHub Actions runs the tests successfully
   - Remove any test skipping for Docker environments

## Success Criteria

1. tex2lyx runs without "User directory does not exist" error
2. All tex2lyx tests pass in Docker environment
3. No hacky workarounds needed in Python code
4. Solution is maintainable and doesn't significantly increase Docker image size

## Notes

- The LyX user directory issue is common in containerized environments
- Some Linux distributions package LyX differently, which may affect the solution
- Consider documenting the LyX configuration requirements for users who build custom Docker images
