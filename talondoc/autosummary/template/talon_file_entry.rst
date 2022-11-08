{{ entry.name.removesuffix(".talon") | escape | underline }}

.. talon:package:: {{ entry.parent.path }}
  :name: {{ entry.parent.name }}
  :include: {{ entry.path }}
  :exclude: **

.. talon:command-table:: {{ entry.name.removesuffix(".talon") }}
