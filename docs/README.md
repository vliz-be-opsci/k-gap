# K-GAP Documentation

Welcome to the K-GAP (Knowledge Graph Analysis Platform) documentation!

## Documentation Structure

This documentation is organized to help you get started quickly and find detailed information when needed.

### Getting Started

- **[Main Documentation (index.md)](./index.md)** - Start here for an overview, architecture, and getting started guide
- **[Quick Reference](./quick-reference.md)** - Quick commands and common patterns
- **[FAQ](./faq.md)** - Answers to frequently asked questions

### Component Documentation

Detailed documentation for each K-GAP component:

- **[GraphDB Component](./components/graphdb.md)** - RDF triple store and SPARQL endpoint
- **[Jupyter Component](./components/jupyter.md)** - Interactive notebooks for data analysis
- **[Sembench Component](./components/sembench.md)** - Automated semantic processing engine
- **[LDES Consumer Component](./components/ldes-consumer.md)** - Multi-feed LDES harvesting service

### Advanced Topics

- **[Advanced Topics](./advanced-topics.md)** - Deep dives into:
  - Assertion paths and dereferencing patterns
  - Custom SPARQL query templates
  - Data validation patterns
  - Performance optimization
  - Multi-repository setup

### Publishing

- **[GitHub Pages Setup](./GITHUB_PAGES.md)** - How to publish this documentation as a website

## Quick Links

### Access K-GAP Services

Once K-GAP is running, access these services:

- **GraphDB Workbench**: http://localhost:7200
- **Jupyter Notebooks**: http://localhost:8889  
- **YASGUI (SPARQL UI)**: http://localhost:8080

### Quick Start

```bash
git clone https://github.com/vliz-be-opsci/k-gap.git
cd k-gap
cp dotenv-example .env
mkdir -p ./data ./notebooks
docker compose up -d
```

### Common Commands

```bash
# View logs
docker compose logs -f

# Restart a service
docker compose restart graphdb

# Stop all services
docker compose down
```

## Documentation Features

### What's Covered

✅ Complete architecture overview  
✅ Component-by-component documentation  
✅ Configuration guides  
✅ Usage examples and patterns  
✅ SPARQL query templates  
✅ Troubleshooting guides  
✅ Performance optimization  
✅ Security considerations  
✅ Integration examples  

### Navigation Tips

1. **New users**: Start with [index.md](./index.md)
2. **Quick answers**: Check [FAQ](./faq.md) or [Quick Reference](./quick-reference.md)
3. **Deep dives**: Explore [Advanced Topics](./advanced-topics.md)
4. **Specific components**: Go directly to component docs in `components/`
5. **Publishing**: See [GitHub Pages Setup](./GITHUB_PAGES.md)

## Contributing to Documentation

Found an error or want to improve the docs?

1. Edit the relevant `.md` file
2. Submit a pull request
3. Documentation will be automatically updated when merged

## Documentation Format

All documentation is written in Markdown and can be:
- Read directly on GitHub
- Published to GitHub Pages
- Rendered in any Markdown viewer
- Converted to other formats (PDF, HTML, etc.)

## Support

For questions about the documentation or K-GAP:

- **Issues**: https://github.com/vliz-be-opsci/k-gap/issues
- **Organization**: https://github.com/vliz-be-opsci

## License

Documentation is part of the K-GAP project and licensed under the MIT License.
