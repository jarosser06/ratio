# Ratio Shell

## Overview

Ratio Shell is an interactive command-line interface wrapper for the Ratio CLI that provides a more user-friendly environment for
interacting with the Ratio AI Operating System. It offers familiar Unix-like command aliases, colored output, and persistent history
while maintaining access to all standard Ratio CLI functionality.

## Features

- **Interactive Shell**: Provides a persistent, interactive environment for Ratio commands
- **Command Aliases**: Familiar Unix-style commands (ls, cd, pwd, cat, etc.)
- **Profile Management**: Auto-detection and selection of Ratio profiles
- **Command History**: Persistent command history across sessions
- **Colorized Output**: Enhanced readability with color-coded prompts and responses
- **System Command Access**: Execute local system commands via the `sys` prefix
- **Custom Script Support**: Run custom scripts from the bin directory
- **Working Directory Management**: Automatic initialization and tracking of current directory

## Installation

Place the [`ratio-shell`](../utils/ratio-shell) script in your PATH and make it executable:

```bash
chmod +x ratio-shell
```

## Usage

### Starting the Shell

```bash
./ratio-shell
```

### Shell Interface

The prompt displays useful context information:

```
(deployment_id) entity_id@current_directory λ
```

Example:
```
(dev) admin@/home/admin λ
```

### Basic Commands

| Command | Description | Ratio CLI Equivalent |
|---------|-------------|----------------------|
| `ls` | List files | `rto list-files` |
| `cd <dir>` | Change directory | `rto change-directory` |
| `pwd` | Print working directory | `rto print-working-directory` |
| `cat <file>` | View file contents | `rto get-file` |
| `mkdir <dir>` | Create directory | `rto create-directory` |
| `rm <file>` | Delete file | `rto delete-file` |
| `chmod <perms> <file>` | Change file permissions | `rto chmod` |
| `chown <owner> <file>` | Change file owner | `rto chown` |

### System Commands

To run commands on your local system (not in the Ratio environment):

```
(dev) admin@/home/admin λ sys ls
```

### Custom Scripts

You can create custom scripts in `$HOME/.ratio/shell/bin/` that will be automatically available as commands in the Ratio Shell.

### Getting Help

```
(dev) admin@/home/admin λ help
```

### Exiting the Shell

```
(dev) admin@/home/admin λ exit
```
or
```
(dev) admin@/home/admin λ quit
```

## Configuration

### Shell Home Directory

The shell stores configuration in `$HOME/.ratio/shell/`:
- `$HOME/.ratio/shell/bin/` - Directory for custom scripts
- `$HOME/.ratio/shell/history/` - Command history storage

### Profile Selection

On startup, the shell automatically detects the default Ratio profile.

## Examples

```
# List files in current directory
(dev) admin@/home/admin λ ls

# Create a directory
(dev) admin@/home/admin λ mkdir new_directory

# Change to that directory
(dev) admin@/home/admin λ cd new_directory

# Create a file
(dev) admin@/new_directory λ cat > myfile.txt
# Enter content, press Ctrl+D when done

# View file content
(dev) admin@/new_directory λ cat myfile.txt

# Run a system command
(dev) admin@/new_directory λ sys date

# See last command's exit status
(dev) admin@/new_directory λ $?
```

## Integration with Ratio

Ratio Shell integrates seamlessly with the existing Ratio CLI, providing a more interactive experience while maintaining full
compatibility with the underlying commands and functionality. All standard Ratio CLI commands are available directly in the shell.