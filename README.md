^[![Build status](https://github.com/sanskrit-coders/video_curation/workflows/Python%20package/badge.svg)](https://github.com/sanskrit-coders/video_curation/actions)
[![Build Status](https://travis-ci.org/sanskrit-coders/video_curation.svg?branch=master)](https://travis-ci.org/sanskrit-coders/video_curation)
[![Documentation Status](https://readthedocs.org/projects/video_curation/badge/?version=latest)](http://video_curation.readthedocs.io/en/latest/?badge=latest)

## Video curation

A package for curating video file collections, with ability to sync with youtube and archive.org video items. 

# For users
* [Autogenerated Docs on readthedocs (might be broken)](http://video_curation.readthedocs.io/en/latest/).
* Manually and periodically generated docs [here](https://sanskrit-coders.github.io/video_curation/build/html/)
* For detailed examples and help, please see individual module files in this package.


## Installation or upgrade:
* `sudo pip install video_curation -U`
* `sudo pip install git+https://github.com/sanskrit-coders/video_curation/@master -U`
* [Web](https://pypi.python.org/pypi/video_curation).


# For contributors

## Contact

Have a problem or question? Please head to [github](https://github.com/sanskrit-coders/video_curation).

## Packaging

* ~/.pypirc should have your pypi login credentials.
```
python setup.py bdist_wheel
twine upload dist/* --skip-existing
```

## Build documentation
- sphinx html docs can be generated with `cd docs; make html`

## Testing
Run `pytest` in the root directory.

## Auxiliary tools
- [![Build Status](https://travis-ci.org/sanskrit-coders/video_curation.svg?branch=master)](https://travis-ci.org/sanskrit-coders/video_curation)
- [![Documentation Status](https://readthedocs.org/projects/video_curation/badge/?version=latest)](http://video_curation.readthedocs.io/en/latest/?badge=latest)
- [pyup](https://pyup.io/account/repos/github/sanskrit-coders/video_curation/)