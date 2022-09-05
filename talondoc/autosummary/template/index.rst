{{ name | escape | title | underline }}

.. talon:package:: {{ path }}
  :name: {{ name }}
  {% if include %}
  :include: {{ include | join(",") }}
  {% endif %}
  {% if exclude %}
  :exclude: {{ exclude | join(",") }}
  {% endif %}
  {% if trigger %}
  :trigger: {{ trigger | join(",") }}
  {% endif %}

.. toctree::
{% for file in toc %}
  {{ file }}
{% endfor %}
