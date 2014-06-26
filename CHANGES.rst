==============================
Turbulenz Python Tools Changes
==============================

.. contents::
    :local:

.. _version-1.x-dev:

1.x-dev
-------

2014-06-26

- Mesh.convex_hulls now raises a ValueError if the input mesh doesn't meet the specified conversion
  parameters rather than returning None.

.. _version-1.0.6:

1.0.6
-----

:release-date: 2014-06-24

- Added 'webworker' and 'webworker-debug' build modes to MakeTZJS
- Fix further issues with non-ascii encoded input files
- Fix for canvas elements not getting correct touch events on some browsers

.. _version-1.0.5:

1.0.5
-----

:release-date: 2014-02-03

- Add support for non-ascii encoded source files in makehtml and maketzjs
- Fix missing dependency on urllib3 for the export events tool
- Fix incorrect log call in dae2json

.. _version-1.0.4:

1.0.4
-----

:release-date: 2013-10-30

- Fix support for multiple animation elements targeting the same attribute
- Fix scale animation export when stored as separate axis components
- Fix dae2json referencing a legacy flat effect in the shaders

.. _version-1.0.3:

1.0.3
-----

:release-date: 2013-10-08

- Updated exportevents tool to support latest format of metrics from the Hub
- Added support for a physics material to be exported in dae2json
- Updated code to conform to Pylint 1.0.0 and updated .pylintrc file with new settings
- Minor bugfixes in json2json tool

.. _version-1.0.2:

1.0.2
-----

:release-date: 2013-07-30

- Updated obj2json tool to support variable numbers of components, fix issues with no uv sets, fix degenerate removal
- Prevent error when running exportevents tool against unpublished projects
- Update exportevents tool to remove the requirement of PyCrypto
- Refactored the exportevents tool to more correctly deal with requests for realtime events
- Updated exportevents tool to support a future format of event downloads

.. _version-1.0.1:

1.0.1
-----

:release-date: 2013-05-20

- Fix exportevents tool when working with encrypted data stored in the local filesystem
- Update exportevents tool to support gzipped responses for efficient download of user metrics

.. _version-1.0:

1.0
---

:release-date: 2013-05-02

.. _v1.0-changes:

- First open source release
