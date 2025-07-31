# MESA Development Container

This dev container provides a complete development environment for the MESA project with pixi package management and visualization capabilities.

## Features

- **Ubuntu 22.04** base with all necessary development tools
- **Pixi** package manager pre-installed
- **C/C++ development tools** (CMake, Ninja, GCC/Clang)
- **Python 3.10** with scientific computing libraries
- **Visualization support** with OpenGL, Jupyter, Matplotlib, Plotly, and more
- **VS Code extensions** for C++, Python, CMake, and TOML development

## Quick Start

1. **Open in Dev Container**: VS Code should automatically detect the dev container configuration and prompt you to reopen in container.

2. **Install dependencies**: Once the container is running, install the project dependencies:
   ```bash
   pixi install
   ```

3. **Build the project**:
   ```bash
   pixi run build-gtsam  # Build GTSAM first
   pixi run build-jrl    # Build JRL
   pixi run build        # Build MESA
   ```

## Available Pixi Tasks

- `pixi run build-gtsam` - Build GTSAM library
- `pixi run build-jrl` - Build JRL library  
- `pixi run build` - Build the main MESA project
- `pixi run jupyter` - Start Jupyter Lab server
- `pixi run notebook` - Start Jupyter Notebook server
- `pixi run plot-results` - Run result plotting script
- `pixi run plot-jrl` - Run JRL plotting script

## Visualization

The container includes several visualization tools:

- **Matplotlib** for 2D plotting
- **Plotly** for interactive plots
- **Jupyter Lab/Notebook** for interactive development
- **Bokeh** for web-based visualizations
- **Seaborn** for statistical plotting

### Jupyter Access

Start Jupyter Lab:
```bash
pixi run jupyter
```

The server will be available at `http://localhost:8888` and VS Code will automatically forward the port.

## Graphics Support

The container includes OpenGL support for 3D visualization. If you need GUI applications, ensure X11 forwarding is enabled on your host system.

## Container Ports

The following ports are automatically forwarded:
- `8080` - Web Server
- `8888` - Jupyter Lab/Notebook
- `5000` - Flask/Debug Server  
- `3000` - Development Server

## Development Tools

Pre-installed VS Code extensions:
- C/C++ Extension Pack
- CMake Tools
- Python with debugging support
- TOML syntax highlighting
- GitHub Copilot
- Linting and formatting tools

## Troubleshooting

### Python Environment Issues
If you encounter Python path issues, the container uses pixi's Python installation. You can verify with:
```bash
which python
pixi run python --version
```

### Build Issues
Ensure you build dependencies in order:
1. GTSAM (`pixi run build-gtsam`)
2. JRL (`pixi run build-jrl`) 
3. MESA (`pixi run build`)

### Graphics Issues
For GUI applications, ensure your host system supports X11 forwarding. On Windows with WSL2, you may need an X server like VcXsrv.
