# Publishing K-GAP Documentation to GitHub Pages

This guide explains how to publish the K-GAP documentation as a website using GitHub Pages.

## Overview

The K-GAP documentation is structured to be published on GitHub Pages, making it accessible as a website at:
```
https://vliz-be-opsci.github.io/k-gap/
```

The documentation is **automatically built and deployed** using a GitHub Actions workflow whenever changes are pushed to the `main` branch.

## Setup Instructions

### 1. Enable GitHub Pages

1. Go to the repository on GitHub: https://github.com/vliz-be-opsci/k-gap
2. Navigate to **Settings** → **Pages**
3. Under **Build and deployment**, select:
   - **Source**: `GitHub Actions`
   - (The workflow is configured to deploy automatically)
4. Optionally configure a custom domain under **Custom domain**

### 2. Automatic Deployment

The documentation is automatically built and deployed by the `Deploy Documentation` GitHub Actions workflow (`.github/workflows/deploy-docs.yml`) whenever:
- Changes are pushed to the `main` branch
- The `docs/` directory is modified
- The workflow file is updated
- Workflow is run manually via "Run workflow" button

**Monitor deployment**:
1. Go to the **Actions** tab in the repository
2. Look for the "Deploy Documentation" workflow
3. Wait for it to complete (green checkmark = success)

### 3. Manual Deployment

To manually trigger a deployment:
1. Go to **Actions** tab
2. Select **Deploy Documentation** workflow on the left
3. Click **Run workflow** → **Branch: main** → **Run workflow**

### 4. Access the Documentation

Once deployed (1-2 minutes), the documentation will be available at:
```
https://vliz-be-opsci.github.io/k-gap/
```

## Local Testing

To test the documentation locally before deploying:

```bash
# Install MyST CLI (if not already installed)
npm install -g mystmd

# Build documentation
cd docs
myst build --html

# Serve locally (from docs/_build/html)
python -m http.server --directory _build/html 8000

# Visit http://localhost:8000/
```

Then make changes to markdown files, rebuild with `myst build --html`, and refresh the browser to see them.

## MyST Configuration

The documentation is built using MyST Markdown. Check `docs/myst.yml` for build configuration if it exists, or MyST will use sensible defaults.

## Documentation Structure

The documentation is organized as follows:

```
docs/
├── _config.yml              # Jekyll configuration (not used with MyST)
├── myst.yml                 # MyST configuration (optional)
├── index.md                 # Main documentation page
├── workflow.md              # Workflow guide
├── configuration-guide.md   # Configuration reference
├── quick-reference.md       # Quick commands reference
├── advanced-topics.md       # Advanced patterns
├── faq.md                   # Frequently asked questions
├── GITHUB_PAGES.md          # This file
└── components/              # Component-specific documentation
    ├── graphdb.md          # GraphDB component
    ├── jupyter.md          # Jupyter component
    ├── sembench.md         # Sembench component
    └── ldes-consumer.md    # LDES Consumer component
```

## Theme and Styling

The documentation uses MyST Markdown with a standard clean theme, providing:
- Left sidebar navigation (auto-generated from page structure)
- Built-in search across pages
- Responsive layout (mobile-friendly)
- Syntax highlighting for code blocks
- Support for complex markdown and interactive content

## Customization

### MyST Configuration

Create or edit `docs/myst.yml` to customize the build process:

```yaml
version: 1.1
project:
  title: K-GAP Documentation
  description: Knowledge Graph Analysis Platform
execution:
  execute: false  # Don't execute code cells
html:
  # HTML-specific settings
  canonical_url: https://vliz-be-opsci.github.io/k-gap/
```

For available options, see [MyST Documentation](https://mystmd.org/guide/configuration).

### Custom Domain

To use a custom domain:

1. Add a `CNAME` file in the `docs/` directory:
   ```
   docs.k-gap.example.com
   ```

2. Configure DNS records with your domain provider:
   ```
   CNAME docs.k-gap -> vliz-be-opsci.github.io
   ```

3. In GitHub repository settings, enter your custom domain under **Settings** → **Pages** → **Custom domain**

To preview the documentation locally before publishing:

### Using Jekyll

1. Install Ruby and Jekyll:
   ```bash
   # macOS
   brew install ruby
   gem install jekyll bundler
   
   # Ubuntu/Debian
   sudo apt-get install ruby-full build-essential
   gem install jekyll bundler
   ```

2. Create a `Gemfile` in the `docs/` directory:
   ```ruby
   source 'https://rubygems.org'
   gem 'github-pages', group: :jekyll_plugins
   gem 'webrick'
   ```

3. Install dependencies:
   ```bash
   cd docs
   bundle install
   ```

4. Serve locally:
   ```bash
   bundle exec jekyll serve
   ```

5. Open http://localhost:4000 in your browser

### Using Docker

```bash
docker run --rm -v "$PWD/docs:/srv/jekyll" -p 4000:4000 jekyll/jekyll jekyll serve
```

Then open http://localhost:4000

## Updating Documentation

To update the published documentation:

1. Edit files in the `docs/` directory
2. Commit and push changes to the `main` branch:
   ```bash
   git add docs/
   git commit -m "Update documentation"
   git push origin main
   ```
3. GitHub Pages will automatically rebuild and deploy (1-2 minutes)

## Troubleshooting

### Documentation Not Updating

- Check the **Actions** tab for build errors
- Verify GitHub Pages is still enabled in Settings
- Clear your browser cache
- Wait a few minutes for propagation

### Build Failures

Common issues:
- Invalid YAML in `_config.yml`
- Broken Markdown links
- Unsupported Jekyll plugins

Check the Actions tab for specific error messages.

### 404 Errors

- Ensure the branch and folder are correctly set in Pages settings
- Verify `index.md` exists in the `docs/` directory
- Check that file paths are correct (case-sensitive)

## Best Practices

1. **Test Locally**: Preview changes before pushing
2. **Use Relative Links**: Link to other documentation pages using relative paths
3. **Maintain Structure**: Keep the existing directory structure
4. **Update Index**: When adding new pages, link them from `index.md`
5. **Check Links**: Regularly verify all links work
6. **Mobile-Friendly**: Test on mobile devices
7. **Search Engine**: Add a `sitemap.xml` for better SEO

## Adding Search Functionality

To add search to the documentation:

1. Use a third-party service like [Algolia DocSearch](https://docsearch.algolia.com/)
2. Or add a simple JavaScript-based search using [Lunr.js](https://lunrjs.com/)

Example with Lunr.js (add to `_layouts/default.html`):
```html
<script src="https://unpkg.com/lunr/lunr.js"></script>
<script>
  // Search implementation
</script>
```

## Related Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [Markdown Guide](https://www.markdownguide.org/)
- [Supported Themes](https://pages.github.com/themes/)

## Support

For issues with GitHub Pages:
- [GitHub Pages Help](https://docs.github.com/en/pages)
- [GitHub Community](https://github.community/)

For K-GAP documentation issues:
- [K-GAP Issues](https://github.com/vliz-be-opsci/k-gap/issues)
