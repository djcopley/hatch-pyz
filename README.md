# Hatch PYZ Plugin

This [Hatch](https://hatch.pypa.io/latest/) plugin provides a custom builder for creating
Python [zip applications](https://docs.python.org/3/library/zipapp.html) (zipapps). This is useful for distributing
Python applications as single-file executables, simplifying deployment and distribution.

The plugin generates a zipapp with all the contents bundled into a single executable file. By default, the generated
zipapp includes all necessary dependencies and can be configured to run a specified entry point.

## Features

- **Single-file Executable**: Combines your application and dependencies into a single zip file.
- **Customizable Entry Point**: Specify the main module or script to be executed.
- **Bundled Dependencies**: Include all necessary Python dependencies within your zipapp

## Example

Here’s an example project directory:

```
.
├── pyproject.toml
├── LICENSE.txt
├── README.md
├── src
│   ├── my_module
│   │   ├── __init__.py
│   │   └── main.py
└── tests
    └── test_main.py
```

And a `pyproject.toml` file that looks like this:

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-pyz",
]
build-backend = "hatchling.build"

[project]
name = "my-python-app"
version = "1.0.0"

[tool.hatch.build.targets.pyz]
interpreter = "/usr/bin/env python3"
main = "my_module.main:main"
compressed = true
```

To build the zipapp, run:

```sh
hatch build --target pyz
```

This command will create an executable zipapp named `dist/my_python_app-1.0.0.pyz`.

## Usage

You can run the generated zipapp directly:

```sh
python dist/my_python_app-1.0.0.pyz
```

## Options

| Option                | Type   | Requirement | Default                | Description                                                                                      |
|-----------------------|--------|-------------|------------------------|--------------------------------------------------------------------------------------------------|
| `main`                | `str`  | Required    |                        | Zipapp entry-point in the format "pkg.mod:func"                                                  |
| `interpreter`         | `str`  | Optional    | `/usr/bin/env python3` | Sets the python interpreter shebang for the archive                                              |
| `compressed`          | `bool` | Optional    | `false`                | If true, files are compressed with the deflate method; otherwise, files are stored uncompressed. |
| `bundle-dependencies` | `bool` | Optional    | `true`                 | if true, pure-python dependencies are bundled in the zipapp archive                              |

## Reproducible Builds

The plugin supports reproducible builds by ensuring consistent metadata and timestamps within the zipapp. This is useful
for verifying that builds produced in different environments are identical. You can control the timestamp used for
reproducible builds via the `SOURCE_DATE_EPOCH` environment variable.

For more details, refer to Hatch’s [Build Configuration](https://hatch.pypa.io/latest/config/build/) documentation.