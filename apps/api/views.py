from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response

from apps.catalog.selectors import (
    get_products,
)
from apps.inventory.selectors import (
    get_inventory_balances,
    get_stock_movements,
)
from apps.inventory.services import (
    InventoryError,
)
from apps.orders.models import (
    Order,
    OrderItem,
)
from apps.orders.selectors import (
    get_order_detail,
    get_orders,
)
from apps.orders.services import (
    OrderError,
    add_order_item,
    cancel_order,
    confirm_order,
    create_order,
    remove_order_item,
    update_order_item_quantity,
)

from .permissions import (
    HasDjangoModelPermissions,
)
from .serializers import (
    InventoryBalanceSerializer,
    OrderActionSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderItemCreateSerializer,
    OrderItemUpdateSerializer,
    OrderListSerializer,
    ProductSerializer,
    StockMovementSerializer,
)


class PermissionProtectedAPIView:
    permission_classes = (
        IsAuthenticated,
        HasDjangoModelPermissions,
    )


def get_api_order_or_404(
    order_id,
):
    try:
        return get_order_detail(
            order_id
        )

    except Order.DoesNotExist as exc:
        raise Http404(
            "Order not found."
        ) from exc


def order_detail_response(
    order_id,
):
    order = get_api_order_or_404(
        order_id
    )

    serializer = OrderDetailSerializer(
        order
    )

    return Response(
        serializer.data
    )


class ProductListAPIView(
    PermissionProtectedAPIView,
    ListAPIView,
):
    serializer_class = ProductSerializer

    required_permissions = {  # noqa: RUF012
        "GET": (
            "catalog.view_product",
        ),
    }

    def get_queryset(self):
        return get_products(
            search=self.request.query_params.get(
                "q",
                "",
            ).strip(),
            category=self.request.query_params.get(
                "category",
                "",
            ),
            supplier=self.request.query_params.get(
                "supplier",
                "",
            ),
            stock_status=self.request.query_params.get(
                "status",
                "",
            ),
            active=self.request.query_params.get(
                "active",
                "active",
            ),
        )


class InventoryListAPIView(
    PermissionProtectedAPIView,
    ListAPIView,
):
    serializer_class = (
        InventoryBalanceSerializer
    )

    required_permissions = {  # noqa: RUF012
        "GET": (
            "inventory.view_inventorybalance",
        ),
    }

    def get_queryset(self):
        return get_inventory_balances(
            search=self.request.query_params.get(
                "q",
                "",
            ).strip(),
            category=self.request.query_params.get(
                "category",
                "",
            ),
            stock_status=self.request.query_params.get(
                "status",
                "",
            ),
            active=self.request.query_params.get(
                "active",
                "active",
            ),
        )


class MovementListAPIView(
    PermissionProtectedAPIView,
    ListAPIView,
):
    serializer_class = (
        StockMovementSerializer
    )

    required_permissions = {  # noqa: RUF012
        "GET": (
            "inventory.view_stockmovement",
        ),
    }

    def get_queryset(self):
        return get_stock_movements(
            search=self.request.query_params.get(
                "q",
                "",
            ).strip(),
            movement_type=(
                self.request.query_params.get(
                    "type",
                    "",
                )
            ),
        )


class OrderListCreateAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    serializer_class = OrderCreateSerializer

    required_permissions = {  # noqa: RUF012
        "GET": (
            "orders.view_order",
        ),
        "POST": (
            "orders.add_order",
        ),
    }

    def get_queryset(self):
        return get_orders(
            search=self.request.query_params.get(
                "q",
                "",
            ).strip(),
            status=self.request.query_params.get(
                "status",
                "",
            ),
        )

    def get(self, request):
        orders = self.get_queryset()

        page = self.paginate_queryset(
            orders
        )

        serializer = OrderListSerializer(
            page,
            many=True,
        )

        return self.get_paginated_response(
            serializer.data
        )

    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        order = create_order(
            customer_name=(
                serializer.validated_data[
                    "customer_name"
                ]
            ),
            notes=(
                serializer.validated_data[
                    "notes"
                ]
            ),
            created_by=request.user,
        )

        order = get_api_order_or_404(
            order.pk
        )

        return Response(
            OrderDetailSerializer(
                order
            ).data,
            status=status.HTTP_201_CREATED,
        )


class OrderDetailAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    queryset = Order.objects.all()

    required_permissions = {  # noqa: RUF012
        "GET": (
            "orders.view_order",
        ),
    }

    serializer_class = (
        OrderDetailSerializer
    )

    def get(
        self,
        request,
        order_id,
    ):
        order = get_api_order_or_404(
            order_id
        )

        serializer = (
            OrderDetailSerializer(
                order
            )
        )

        return Response(
            serializer.data
        )


class OrderItemCreateAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    queryset = Order.objects.all()

    required_permissions = {  # noqa: RUF012
        "POST": (
            "orders.add_orderitem",
        ),
    }

    serializer_class = (
        OrderItemCreateSerializer
    )

    def post(
        self,
        request,
        order_id,
    ):
        order = get_object_or_404(
            Order,
            pk=order_id,
        )

        serializer = (
            OrderItemCreateSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            add_order_item(
                order=order,
                product=(
                    serializer.validated_data[
                        "product"
                    ]
                ),
                quantity=(
                    serializer.validated_data[
                        "quantity"
                    ]
                ),
            )

        except OrderError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        return order_detail_response(
            order.pk
        )


class OrderItemDetailAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    queryset = OrderItem.objects.all()

    required_permissions = {  # noqa: RUF012
        "PATCH": (
            "orders.change_orderitem",
        ),
        "DELETE": (
            "orders.change_orderitem",
        ),
    }

    serializer_class = (
        OrderItemUpdateSerializer
    )

    def get_item(
        self,
        order_id,
        item_id,
    ):
        return get_object_or_404(
            OrderItem,
            pk=item_id,
            order_id=order_id,
        )

    def patch(
        self,
        request,
        order_id,
        item_id,
    ):
        item = self.get_item(
            order_id,
            item_id,
        )

        serializer = (
            OrderItemUpdateSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            update_order_item_quantity(
                item=item,
                quantity=(
                    serializer.validated_data[
                        "quantity"
                    ]
                ),
            )

        except OrderError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        return order_detail_response(
            order_id
        )

    def delete(
        self,
        request,
        order_id,
        item_id,
    ):
        item = self.get_item(
            order_id,
            item_id,
        )

        try:
            remove_order_item(
                item=item
            )

        except OrderError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        return order_detail_response(
            order_id
        )


class OrderConfirmAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    queryset = Order.objects.all()

    required_permissions = {  # noqa: RUF012
        "POST": (
            "orders.confirm_order",
        ),
    }

    serializer_class = (
        OrderActionSerializer
    )

    def post(
        self,
        request,
        order_id,
    ):
        order = get_object_or_404(
            Order,
            pk=order_id,
        )

        try:
            confirm_order(
                order=order,
                confirmed_by=request.user,
            )

        except (
            OrderError,
            InventoryError,
        ) as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        return order_detail_response(
            order.pk
        )


class OrderCancelAPIView(
    PermissionProtectedAPIView,
    GenericAPIView,
):
    queryset = Order.objects.all()

    required_permissions = {  # noqa: RUF012
        "POST": (
            "orders.cancel_order",
        ),
    }

    serializer_class = (
        OrderActionSerializer
    )

    def post(
        self,
        request,
        order_id,
    ):
        order = get_object_or_404(
            Order,
            pk=order_id,
        )

        try:
            cancel_order(
                order=order
            )

        except OrderError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        return order_detail_response(
            order.pk
        )