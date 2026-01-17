# Dependency Management Guide

This project uses version ranges in `requirements.txt` to allow automatic updates while maintaining compatibility.

## Current Setup

### Version Strategy

- **Version Ranges**: Dependencies use `>=X.Y.Z,<next_major` format
  - Allows automatic patch and minor version updates
  - Prevents breaking major version changes
  - Example: `flask>=3.1.2,<4.0.0` allows 3.1.2, 3.1.3, 3.2.0, etc., but not 4.0.0

### Latest Versions (as of update)

- **OpenTelemetry Core**: 1.39.1
- **OpenTelemetry Instrumentation**: 0.49b0+ (beta versions)
- **Flask**: 3.1.2+
- **Other packages**: Updated to latest stable versions

## Updating Dependencies

### Option 1: Automatic Updates (Recommended)

Use the provided script:

```bash
./scripts/update-requirements.sh
```

This script:
- Checks for `requirements.in` and uses `pip-compile` if available
- Otherwise uses `pip-upgrader` or `pip-review`
- Updates to latest compatible versions within the specified ranges

### Option 2: Manual Update with pip-tools

If you have `requirements.in`:

```bash
cd src
pip install pip-tools
pip-compile requirements.in --upgrade
```

This generates a new `requirements.txt` with pinned versions.

### Option 3: Manual Update

Update versions manually in `requirements.txt`:

```bash
# Install latest versions within ranges
pip install --upgrade -r src/requirements.txt
pip freeze > src/requirements.txt.new
# Review and replace requirements.txt
```

## GitHub Actions Automation

A GitHub Action workflow (`.github/workflows/update-dependencies.yml`) automatically:

- Runs weekly (Mondays at 9 AM UTC)
- Updates dependencies using `pip-compile` if `requirements.in` exists
- Creates a Pull Request if updates are available
- Can be manually triggered via "workflow_dispatch"

## Version Range Guidelines

### When to Use Strict Pinning (`==`)

- **Critical security packages**: Pin exact versions
- **Known compatibility issues**: Pin to working version
- **Production deployments**: Consider pinning for reproducibility

### When to Use Ranges (`>=`, `<`)

- **Most dependencies**: Use ranges for auto-updates
- **Well-maintained packages**: Safe to use ranges
- **Development**: Ranges allow easy updates

### Current Ranges

All packages use `>=X.Y.Z,<next_major` format:
- Allows patch updates (bug fixes)
- Allows minor updates (new features, backward compatible)
- Prevents major updates (breaking changes)

## OpenTelemetry Notes

- **Core packages** (api, sdk): Updated to 1.39.1
- **Instrumentation packages**: Use beta versions (0.49b0+)
- **Jaeger exporter**: Deprecated but kept for compatibility
  - Consider migrating to OTLP exporter only in the future
- **OTLP exporter**: Preferred modern approach (1.39.1)

## Troubleshooting

### Dependency Conflicts

If you encounter conflicts:

1. Check for incompatible version ranges
2. Review error messages for specific packages
3. Temporarily pin conflicting packages to exact versions
4. Test thoroughly before committing

### Breaking Changes

If an update breaks functionality:

1. Revert the specific package version
2. Pin to the last known working version
3. Report the issue to the package maintainer
4. Update your version range to exclude the problematic version

### Testing Updates

Always test after updating dependencies:

```bash
# Install updated dependencies
pip install -r src/requirements.txt

# Run your application
python src/main.py

# Run tests (if available)
# pytest tests/
```

## Best Practices

1. **Review PRs**: Always review automated dependency update PRs
2. **Test locally**: Test updates in a development environment first
3. **Keep ranges reasonable**: Don't use overly broad ranges (e.g., `>=1.0.0`)
4. **Document exceptions**: If you pin a package, document why
5. **Regular updates**: Don't let dependencies get too outdated

## Files

- `src/requirements.txt`: Main requirements file with version ranges
- `src/requirements.in`: Loose dependency specs for pip-tools (optional)
- `scripts/update-requirements.sh`: Update script
- `.github/workflows/update-dependencies.yml`: Automated updates
