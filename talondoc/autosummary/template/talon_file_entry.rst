{{ entry.get_name().removesuffix(".talon") | escape | underline }}

.. talon:package:: {{ entry.get_parent().get_path() }}
  :name: {{ entry.get_parent().get_name() }}
  :include: {{ entry.get_path() }}
  :exclude: **

.. talon:command-table:: {{ entry.get_name().removesuffix(".talon") }}
