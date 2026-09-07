from rest_framework import serializers

from apps.catalog.models import (
    Category,
    Product,
    Supplier,
)
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)
from apps.orders.models import (
    Order,
    OrderItem,
)


class CategorySummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
        )


class SupplierSummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
        )


class ProductSummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Product
        fields = (
            "id",
            "sku",
            "name",
        )


class ProductSerializer(
    serializers.ModelSerializer
):
    category = CategorySummarySerializer(
        read_only=True
    )

    supplier = SupplierSummarySerializer(
        read_only=True
    )

    stock_quantity = serializers.IntegerField(
        read_only=True
    )

    stock_status = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = Product

        fields = (
            "id",
            "sku",
            "name",
            "category",
            "supplier",
            "price",
            "minimum_stock",
            "stock_quantity",
            "stock_status",
            "active",
        )


class InventoryBalanceSerializer(
    serializers.ModelSerializer
):
    product = ProductSummarySerializer(
        read_only=True
    )

    minimum_stock = serializers.IntegerField(
        source="product.minimum_stock",
        read_only=True,
    )

    stock_status = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = InventoryBalance

        fields = (
            "id",
            "product",
            "quantity",
            "minimum_stock",
            "stock_status",
            "updated_at",
        )


class StockMovementSerializer(
    serializers.ModelSerializer
):
    product = ProductSummarySerializer(
        read_only=True
    )

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
        allow_null=True,
    )

    created_by = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockMovement

        fields = (
            "id",
            "product",
            "movement_type",
            "quantity_delta",
            "quantity_before",
            "quantity_after",
            "reason",
            "order_number",
            "created_by",
            "created_at",
        )


class OrderItemSerializer(
    serializers.ModelSerializer
):
    product = ProductSummarySerializer(
        read_only=True
    )

    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem

        fields = (
            "id",
            "product",
            "quantity",
            "unit_price",
            "line_total",
        )


class OrderListSerializer(
    serializers.ModelSerializer
):
    item_count = serializers.IntegerField(
        read_only=True
    )

    total_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    created_by = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Order

        fields = (
            "id",
            "order_number",
            "customer_name",
            "status",
            "item_count",
            "total_amount",
            "created_by",
            "created_at",
        )


class OrderDetailSerializer(
    serializers.ModelSerializer
):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    total = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    created_by = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True,
    )

    confirmed_by = serializers.CharField(
        source="confirmed_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Order

        fields = (
            "id",
            "order_number",
            "customer_name",
            "notes",
            "status",
            "items",
            "total",
            "created_by",
            "confirmed_by",
            "created_at",
        )


class OrderCreateSerializer(
    serializers.Serializer
):
    customer_name = serializers.CharField(
        max_length=200
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_customer_name(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Customer name is required."
            )

        return value


class OrderItemCreateSerializer(
    serializers.Serializer
):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(
            active=True
        )
    )

    quantity = serializers.IntegerField(
        min_value=1
    )


class OrderItemUpdateSerializer(
    serializers.Serializer
):
    quantity = serializers.IntegerField(
        min_value=1
    )

class OrderActionSerializer(
    serializers.Serializer
):
    pass