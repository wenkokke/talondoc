{{ entry.name.removesuffix(".talon") | escape | underline }}

.. talon:package:: {{ entry.package.path }}
  :name: {{ entry.package.name }}
  :include: {{ entry.path }}
  :exclude: **

.. talon:command-table:: {{ entry.name.removesuffix(".talon") }}
