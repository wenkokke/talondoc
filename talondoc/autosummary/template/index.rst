{{ fullname | escape | underline }}

.. talon:package:: {{ relpath }}
  :name: {{ fullname }}
  {% if default %}
  :default: {{ default }}
  {% endif %}
  {% if include %}
  :include: {{ include | join(,) }}
  {% endif %}
  {% if exclude %}
  :exclude: {{ exclude | join(,) }}
  {% endif %}
  :trigger: ready

.. toctree::
{% for file in files %}
  {{ file }}
{% endfor %}
