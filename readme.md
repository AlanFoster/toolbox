# toolbox

## Installing

Note: When running `git clone`, you will need to configure Git to authenticate with SSH, or you can create a [disposable personal access token](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token#creating-a-token) with access to private repositories enabled and use that in conjunction with your username to authenticate.

```
git clone https://github.com/AlanFoster/toolbox.git
```

Install the dependencies:
```
cd toolbox
git submodule update --init --recursive
pip3 install -r requirements.txt
```

Verify it works:

```
python3 toolbox.py --help
```

## Using Docker


Build the image:

```
docker build -t toolbox .
```

Example usage:

```
docker run -it --rm -p 8000:8000 toolbox /bin/sh -c "python toolbox.py serve -p 8000 ."
```

## Running

### Server

The server will:
- Serve the files within the provided directory
- Serve common CTF tools, such as linpeas.sh and static binaries
- Serve payload/shell generation

Usage:

```
python3 toolbox.py serve -p 8000 .
```

You can now visit the running server at `http://localhost:8000`

![Example of the running server](./images/server.png)

By default the server supports the following files:

- [Payloads](toolbox/server/modules)
- [Common tools](toolbox/config.json)

## Contributing

### Updating requirements.txt

Updating `pipenv` currently requires a manual change to `requirements.txt`.
This file will not contain dev-dependencies and is meant for end-users.

```
pipenv lock -r > requirements.txt
```

### Adding additional tools

You can add additional third party projects by creating a new Git submodule:

```
git submodule add https://github.com/owner/project_name third_party/project_name
```

And updating the associated [configuration file](toolbox/config.json) to include the new tool.

### Running tests

You must first install the developer dependencies:

```shell
pipenv install --dev
```

Running all tests:

```
pytest
```

To run only one set of tests add the focus marker:

```python
@pytest.mark.focus
def test_some_method():
    assert 1 == 1
```

Run with:

```shell
pytest -m focus
```

Add a debugging breakpoint with:

```python
breakpoint()
```

Updating snapshots:

```shell
pytest --snapshot-update
```

## Planned

- Configure setup.py to install only the required source code + datafiles + licenses
- Use gunicorn / uwsgi in 'production' mode
- Add additional files:
  - Static pspy64
  - Static Docker client
