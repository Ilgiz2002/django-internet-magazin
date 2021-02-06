from django import template

register = template.Library()

TABLE_HEAD = """
        <table class="table">
                <tbody>
             """

TABLE_TAIL = """
              </tbody>
            </table>
             """


@register.filter
def product_spec(product):
    print(product)
    pass
