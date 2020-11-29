# toolbox

## Installing

```
git clone https://github.com/AlanFoster/toolbox.git
git submodule update
pip3 install -r requirements.txt
python3 toolbox.py --help
```

## Running

### Server

The server will host files in the current directory as well as additional payloads and common utilities:

```
toolbox serve -p 8000 .
```

You can now visit the running website at `http://localhost:8000`

By default the server supports the following files:
- [Payloads](toolbox/server/templates)
- [Common tools](toolbox/config.json)

### Running tests

```
pipenv install --dev
pytest
```

To run only one set of tests add the focus marker:

```
@pytest.mark.focus
def test_some_method():
    assert 1 == 1
```

Run with:
```
pytest -m focus
```

Add a debugging breakpoint with:

```
breakpoint()
```

Updating snapshots:

```
pytest --snapshot-update
```

### Notes

Adding additional tools:
- `git submodule add https://github.com/foo/bar`

TODO:
- Configure setup.py to install only the required source code + datafiles + licenses
- Use gunicorn / uwsgi in 'production' mode
- Add additional files:
    - static socat
    - static pspy64

## References

- https://python-packaging.readthedocs.io/en/latest/index.html
