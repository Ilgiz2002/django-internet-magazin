import sys

from PIL import Image
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.uploadedfile import InMemoryUploadedFile

from io import BytesIO
from django.urls import reverse

# Используется для того что бы картинку преобразовать в байты на строке 107
User = get_user_model()


# Исльзовать пользователя, который указан в settings.AUTH_USER_MODEL

# Основные модели
# 1 Category
# 2 Product
# 3 CartProduct
# 4 Cart
# 5 Order

# Дополнительные модели
# 6 Customers
# 7 Specification -> Характеристики продукта

def get_product_url(obj, viewname):
    ct_model = obj.__class__._meta.model_name
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug': obj.slug})


class MinResolutionErrorException(Exception):
    pass


class MaxResolutionErrorException(Exception):
    pass


class LatestProductsManager:

    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        # приоритет для какой-то модели
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            # Вызов у модели ContentType родительский класс
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists():
                if with_respect_to in args:
                    return sorted(
                        products,
                        key=lambda x: x.__class__._meta.model_name.startswith(with_respect_to),
                        reverse=True
                                  )
        return products


class LatersProducts:
    """Получение товаров разных моделей в одной через ContentType"""
    objects = LatestProductsManager()


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name='Имя категории')
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):

    MIN_RESOLUTION = (400, 400)
    MAX_RESOLUTION = (800, 800)
    MAX_IMAGE_SIZE = 3145728

    class Meta:
        abstract = True
        # Абстрактная модель ->
        # 1. Невозможно создать миграцию для этой модели
        # 2. Сама по себе ничего не представляет, нужно создать дочерний класс

    category = models.ForeignKey(
        Category,
        verbose_name='Категория',
        on_delete=models.CASCADE
        # удалить все связи с этим объектом
    )

    title = models.CharField(max_length=255, verbose_name='Наименование')
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение')
    desctiption = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name='Цена'
    )

    # max_digits -> из скольки цифр должно состоять число
    # decimal_places -> цифр после запятой

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        image = self.image
        img = Image.open(image)
        # Преобразуем цветовой канал картинки в RGB
        new_img = img.convert('RGB')
        # Уменьшаем размер картинки, ANTIALIAS -> ?
        resized_new_img = new_img.resize((200, 200), Image.ANTIALIAS)
        # Записываем картику в байты
        filestream = BytesIO()
        resized_new_img.save(filestream, 'JPEG', quality=90)

        name = '{}'.format(self.image.name.split('.'))
        self.image = InMemoryUploadedFile(
            filestream, 'ImageField', name, 'jpeg/image', sys.getsizeof(filestream), None
        )
        # img = Image.open(image)
        # min_height, min_width = self.MIN_RESOLUTION
        # max_height, max_width = self.MAX_RESOLUTION
        #
        # if img.height < min_height or img.width < min_width:
        #     raise MinResolutionErrorException(
        #         'Разрешение изображения меньше минимального!')
        # if img.height > max_height or img.width > max_width:
        #     raise MaxResolutionErrorException(
        #         'Разрешение изображения больше максимального!')
        super().save(*args, **kwargs)
        # Если не вызвать родительский метод save -> мы получим ошибку,
        # по той причине, что мы переопределим род. метод


class CartProduct(models.Model):
    user = models.ForeignKey(
        'Customer',
        verbose_name='Покупатель',
        on_delete=models.CASCADE
    )
    cart = models.ForeignKey(
        'Cart',
        verbose_name='Корзина',
        on_delete=models.CASCADE,
        related_name='related_products'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # ContentType - микрофрееймворк, коротый видит все наши модели,
    # коротые есть в INSTALLETED_APPS. Если зайти в админку и посмотреть
    # на это поле
    # можно будет увидеть все модели
    # object_id -> это id экземпляра этой модели (CartProduct)
    # content_object -> генерирует связь ForeignKey

    # product = NoteBook.objects.get(pk=1)
    # cart_product = CartProduct.objects.create(content_object=product)

    quantuty = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name='Общая цена'
    )

    def __str__(self):
        return f'Продукт : {self.content_object.title}'


class Cart(models.Model):
    owner = models.ForeignKey(
        'Customer',
        verbose_name='Владелиц',
        on_delete=models.CASCADE
    )
    produts = models.ManyToManyField(
        CartProduct,
        blank=True,
        related_name='related_cart'
    )
    total_produts = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name='Общая цена'
    )

    def __str__(self):
        return f'{self.id}'


class Customer(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=20, verbose_name='Номер телефона')
    address = models.CharField(max_length=255, verbose_name='Адрес')

    # Использовать first_name и last_name не будем так как эти поля есть
    # в классе User

    def __str__(self):
        return f'Покупатель {self.user.first_name} {self.user.last_name}'


class Notebook(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(
        max_length=255,
        verbose_name='Тип дисплея')
    processor_freq = models.CharField(
        max_length=255,
        verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    video = models.CharField(max_length=255, verbose_name='Видеокарта')
    time_without_charge = models.CharField(
        max_length=255,
        verbose_name='Время работы аккумулятора'
    )

    def __str__(self):
        return f'{self.category.name} {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')


class Smartphone(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(
        max_length=255,
        verbose_name='Тип дисплея')
    reslution = models.CharField(
        max_length=255,
        verbose_name='Разрешение экрана')
    accum_volume = models.CharField(
        max_length=255,
        verbose_name='Объем батареи')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    sd = models.BooleanField(default=True)
    sd_volume_max = models.CharField(
        max_length=255,
        verbose_name='Максимальный объем встраиваемой памяти')
    main_cam_mp = models.CharField(
        max_length=255,
        verbose_name='Главная камера')
    frontal_cam_mp = models.CharField(
        max_length=255,
        verbose_name='Фронтальная камера')

    def __str__(self):
        return f'{self.category.name} {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')
