from django.db import migrations, models
import django.db.models.deletion


def populate_cart_products(apps, schema_editor):
    CartItem = apps.get_model('store', 'CartItem')
    for item in CartItem.objects.select_related('variant').iterator():
        if item.variant_id:
            item.product_id = item.variant.product_id
            item.save(update_fields=['product'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_product_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='product',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='store.product',
            ),
        ),
        migrations.AlterField(
            model_name='cartitem',
            name='variant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='store.productvariant',
            ),
        ),
        migrations.RunPython(populate_cart_products, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cartitem',
            name='product',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cart_items',
                to='store.product',
            ),
        ),
    ]
