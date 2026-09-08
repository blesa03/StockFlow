from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import (
    BaseCommand,
    CommandError,
    call_command,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.roles import (
    MANAGER_GROUP,
    OPERATOR_GROUP,
)
from apps.catalog.models import (
    Category,
    Product,
    Supplier,
)
from apps.inventory.models import (
    StockMovement,
)
from apps.inventory.services import (
    register_stock_entry,
)
from apps.orders.models import Order
from apps.orders.services import (
    add_order_item,
    cancel_order,
    confirm_order,
    create_order,
)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Populate an empty StockFlow database "
        "with realistic showcase data."
    )

    DEMO_PASSWORD = "StockFlowDemo123!"

    def handle(self, *args, **options):
        self._ensure_empty_database()

        self.stdout.write(
            self.style.WARNING(
                "Creating StockFlow showcase data..."
            )
        )

        with transaction.atomic():
            call_command(
                "setup_roles",
                verbosity=0,
            )

            users = self._create_users()
            categories = self._create_categories()
            suppliers = self._create_suppliers()

            products = self._create_products(
                categories,
                suppliers,
            )

            self._create_initial_stock(
                products,
                users,
            )

            self._create_confirmed_orders(
                products,
                users,
            )

            self._create_restock_movements(
                products,
                users,
            )

            self._create_draft_orders(
                products,
                users,
            )

            self._create_cancelled_orders(
                products,
                users,
            )

            self._backdate_user_activity(
                users
            )

        self._print_summary()

    def _ensure_empty_database(self):
        checks = (
            Category.objects.exists(),
            Supplier.objects.exists(),
            Product.objects.exists(),
            Order.objects.exists(),
            StockMovement.objects.exists(),
            User.objects.filter(
                is_superuser=False
            ).exists(),
        )

        if any(checks):
            raise CommandError(
                (
                    "StockFlow already contains operational "
                    "data. Run:\n\n"
                    "python manage.py reset_app_data --yes\n\n"
                    "before seeding showcase data."
                )
            )

    def _create_users(self):
        manager_group = Group.objects.get(
            name=MANAGER_GROUP
        )

        operator_group = Group.objects.get(
            name=OPERATOR_GROUP
        )

        manager = User.objects.create_user(
            username="laura.manager",
            password=self.DEMO_PASSWORD,
            first_name="Laura",
            last_name="Martínez",
            email="laura.martinez@stockflow.local",
        )

        manager.groups.add(
            manager_group
        )

        operator_1 = User.objects.create_user(
            username="david.warehouse",
            password=self.DEMO_PASSWORD,
            first_name="David",
            last_name="Romero",
            email="david.romero@stockflow.local",
        )

        operator_1.groups.add(
            operator_group
        )

        operator_2 = User.objects.create_user(
            username="marta.operations",
            password=self.DEMO_PASSWORD,
            first_name="Marta",
            last_name="Sánchez",
            email="marta.sanchez@stockflow.local",
        )

        operator_2.groups.add(
            operator_group
        )

        return {
            "manager": manager,
            "operator_1": operator_1,
            "operator_2": operator_2,
        }

    def _create_categories(self):
        names = (
            "Keyboards & Mice",
            "Monitors",
            "Storage",
            "Networking",
            "Components",
            "Office Equipment",
            "Accessories",
        )

        return {
            name: Category.objects.create(
                name=name
            )
            for name in names
        }

    def _create_supplier(self, name, **optional):
        field_names = {
            field.name
            for field in Supplier._meta.fields
        }

        data = {
            "name": name,
        }

        for key, value in optional.items():
            if key in field_names:
                data[key] = value

        return Supplier.objects.create(
            **data
        )

    def _create_suppliers(self):
        suppliers = (
            (
                "TechDistribution Iberia",
                {
                    "email": (
                        "sales@techdistribution.local"
                    ),
                    "phone": "+34 950 100 101",
                },
            ),
            (
                "Peripheral Supply Co.",
                {
                    "email": (
                        "orders@peripheralsupply.local"
                    ),
                    "phone": "+34 950 100 102",
                },
            ),
            (
                "NetWholesale Europe",
                {
                    "email": (
                        "sales@netwholesale.local"
                    ),
                    "phone": "+34 950 100 103",
                },
            ),
            (
                "OfficeStock España",
                {
                    "email": (
                        "pedidos@officestock.local"
                    ),
                    "phone": "+34 950 100 104",
                },
            ),
            (
                "Component Hub",
                {
                    "email": (
                        "supply@componenthub.local"
                    ),
                    "phone": "+34 950 100 105",
                },
            ),
        )

        return {
            name: self._create_supplier(
                name,
                **optional,
            )
            for name, optional in suppliers
        }

    def _create_products(
        self,
        categories,
        suppliers,
    ):
        product_data = (
            (
                "KB-LOG-120",
                "Logitech K120",
                "Keyboards & Mice",
                "Peripheral Supply Co.",
                "18.90",
                10,
                54,
            ),
            (
                "MS-LOG-203",
                "Logitech G203",
                "Keyboards & Mice",
                "Peripheral Supply Co.",
                "29.90",
                8,
                31,
            ),
            (
                "KB-KEY-C3P",
                "Keychron C3 Pro",
                "Keyboards & Mice",
                "TechDistribution Iberia",
                "54.90",
                6,
                18,
            ),
            (
                "KB-LOG-MXM",
                "Logitech MX Keys Mini",
                "Keyboards & Mice",
                "Peripheral Supply Co.",
                "89.90",
                4,
                6,
            ),
            (
                "MN-DELL-P24",
                "Dell P2425H",
                "Monitors",
                "TechDistribution Iberia",
                "159.00",
                5,
                12,
            ),
            (
                "MN-LG-27MR4",
                "LG 27MR400",
                "Monitors",
                "TechDistribution Iberia",
                "129.00",
                5,
                16,
            ),
            (
                "MN-SAM-S24",
                "Samsung S24C330",
                "Monitors",
                "TechDistribution Iberia",
                "119.00",
                6,
                19,
            ),
            (
                "SSD-KIN-NV3",
                "Kingston NV3 1TB",
                "Storage",
                "Component Hub",
                "64.90",
                6,
                11,
            ),
            (
                "SSD-SAM-870",
                "Samsung 870 EVO 1TB",
                "Storage",
                "Component Hub",
                "89.90",
                8,
                35,
            ),
            (
                "SSD-WD-SN580",
                "WD Blue SN580 1TB",
                "Storage",
                "Component Hub",
                "72.90",
                8,
                28,
            ),
            (
                "SSD-CRU-BX5",
                "Crucial BX500 500GB",
                "Storage",
                "Component Hub",
                "42.90",
                7,
                21,
            ),
            (
                "NET-TPL-SG8",
                "TP-Link TL-SG108",
                "Networking",
                "NetWholesale Europe",
                "34.90",
                5,
                20,
            ),
            (
                "NET-TPL-AX55",
                "TP-Link Archer AX55",
                "Networking",
                "NetWholesale Europe",
                "89.90",
                4,
                13,
            ),
            (
                "NET-UBI-UX",
                "Ubiquiti UniFi Express",
                "Networking",
                "NetWholesale Europe",
                "139.00",
                3,
                9,
            ),
            (
                "NET-NET-GS8",
                "Netgear GS308",
                "Networking",
                "NetWholesale Europe",
                "29.90",
                4,
                15,
            ),
            (
                "RAM-COR-32",
                "Corsair Vengeance 32GB",
                "Components",
                "Component Hub",
                "79.90",
                6,
                20,
            ),
            (
                "RAM-KIN-FB32",
                "Kingston Fury Beast 32GB",
                "Components",
                "Component Hub",
                "74.90",
                6,
                18,
            ),
            (
                "PSU-BQT-750",
                "be quiet! Pure Power 12 M 750W",
                "Components",
                "Component Hub",
                "109.00",
                3,
                10,
            ),
            (
                "CPU-NOC-U12R",
                "Noctua NH-U12S redux",
                "Components",
                "Component Hub",
                "54.90",
                4,
                13,
            ),
            (
                "CAM-LOG-C920",
                "Logitech C920",
                "Accessories",
                "Peripheral Supply Co.",
                "69.90",
                4,
                14,
            ),
            (
                "HST-JAB-E240",
                "Jabra Evolve2 40",
                "Accessories",
                "Peripheral Supply Co.",
                "109.00",
                3,
                8,
            ),
            (
                "UPS-APC-950",
                "APC Back-UPS 950VA",
                "Office Equipment",
                "OfficeStock España",
                "129.00",
                3,
                9,
            ),
            (
                "PRN-BRO-L24",
                "Brother HL-L2400DW",
                "Office Equipment",
                "OfficeStock España",
                "139.00",
                3,
                7,
            ),
            (
                "PRN-EPS-2850",
                "Epson EcoTank ET-2850",
                "Office Equipment",
                "OfficeStock España",
                "249.00",
                2,
                5,
            ),
            (
                "PRN-CAN-5350",
                "Canon PIXMA TS5350i",
                "Office Equipment",
                "OfficeStock España",
                "84.90",
                2,
                4,
            ),
            (
                "SHR-FEL-8C",
                "Fellowes Powershred 8C",
                "Office Equipment",
                "OfficeStock España",
                "74.90",
                2,
                6,
            ),
            (
                "DOC-KEN-484",
                "Kensington SD4840P Dock",
                "Accessories",
                "TechDistribution Iberia",
                "159.00",
                3,
                7,
            ),
            (
                "HUB-ANK-555",
                "Anker 555 USB-C Hub",
                "Accessories",
                "TechDistribution Iberia",
                "59.90",
                4,
                12,
            ),
            (
                "KB-MS-600",
                "Microsoft Wired Keyboard 600",
                "Keyboards & Mice",
                "Peripheral Supply Co.",
                "19.90",
                5,
                17,
            ),
            (
                "USB-SAN-128",
                "SanDisk Ultra Flair 128GB",
                "Storage",
                "Component Hub",
                "14.90",
                10,
                45,
            ),
        )

        products = {}

        for (
            sku,
            name,
            category,
            supplier,
            price,
            minimum_stock,
            initial_stock,
        ) in product_data:
            product = Product.objects.create(
                sku=sku,
                name=name,
                category=categories[
                    category
                ],
                supplier=suppliers[
                    supplier
                ],
                price=Decimal(price),
                minimum_stock=minimum_stock,
                active=True,
            )

            products[sku] = {
                "object": product,
                "initial_stock": initial_stock,
            }

        return products

    def _create_initial_stock(
        self,
        products,
        users,
    ):
        now = timezone.now()

        operator = users[
            "operator_1"
        ]

        for index, data in enumerate(
            products.values()
        ):
            product = data["object"]

            register_stock_entry(
                product=product,
                quantity=data[
                    "initial_stock"
                ],
                reason=(
                    "Initial warehouse load"
                ),
            )

            movement = (
                StockMovement.objects
                .filter(product=product)
                .order_by("-pk")
                .first()
            )

            StockMovement.objects.filter(
                pk=movement.pk
            ).update(
                created_by=operator,
                created_at=(
                    now
                    - timedelta(
                        days=30
                        - (index % 4)
                    )
                ),
            )

    def _create_confirmed_orders(
        self,
        products,
        users,
    ):
        definitions = (
            (
                "NovaByte Solutions",
                (
                    ("KB-LOG-120", 5),
                    ("MS-LOG-203", 4),
                    ("MN-DELL-P24", 3),
                ),
            ),
            (
                "Almería Office Tech",
                (
                    ("SSD-SAM-870", 4),
                    ("NET-TPL-SG8", 3),
                    ("NET-TPL-AX55", 2),
                ),
            ),
            (
                "Consultoría Levante",
                (
                    ("SSD-KIN-NV3", 4),
                    ("MN-LG-27MR4", 2),
                    ("HST-JAB-E240", 2),
                ),
            ),
            (
                "Mar Azul Coworking",
                (
                    ("KB-LOG-MXM", 6),
                    ("CAM-LOG-C920", 3),
                    ("HUB-ANK-555", 2),
                ),
            ),
            (
                "Sierra Networks",
                (
                    ("NET-UBI-UX", 2),
                    ("NET-NET-GS8", 4),
                    ("SSD-WD-SN580", 3),
                ),
            ),
            (
                "Delta Systems",
                (
                    ("RAM-COR-32", 3),
                    ("RAM-KIN-FB32", 2),
                    ("PSU-BQT-750", 2),
                ),
            ),
            (
                "Grupo Indalo",
                (
                    ("MN-DELL-P24", 5),
                    ("PRN-BRO-L24", 2),
                    ("UPS-APC-950", 2),
                ),
            ),
            (
                "Kiosko Digital",
                (
                    ("SSD-KIN-NV3", 4),
                    ("USB-SAN-128", 8),
                ),
            ),
            (
                "FormaLab",
                (
                    ("PRN-CAN-5350", 4),
                    ("PRN-EPS-2850", 1),
                    ("SHR-FEL-8C", 2),
                ),
            ),
            (
                "Orion Servicios",
                (
                    ("KB-LOG-120", 7),
                    ("MS-LOG-203", 3),
                    ("MN-SAM-S24", 4),
                ),
            ),
            (
                "Costa Sur IT",
                (
                    ("SSD-CRU-BX5", 5),
                    ("CPU-NOC-U12R", 3),
                    ("DOC-KEN-484", 2),
                ),
            ),
            (
                "ByteWorks",
                (
                    ("KB-KEY-C3P", 4),
                    ("KB-MS-600", 5),
                    ("NET-TPL-SG8", 2),
                ),
            ),
        )

        now = timezone.now()

        for index, (
            customer,
            lines,
        ) in enumerate(definitions):
            creator = (
                users["operator_1"]
                if index % 2 == 0
                else users["operator_2"]
            )

            order = create_order(
                customer_name=customer,
                notes=(
                    "Standard business order."
                ),
                created_by=creator,
            )

            for sku, quantity in lines:
                add_order_item(
                    order=order,
                    product=products[
                        sku
                    ]["object"],
                    quantity=quantity,
                )

            confirm_order(
                order=order,
                confirmed_by=users[
                    "manager"
                ],
            )

            order_date = (
                now
                - timedelta(
                    days=24 - index * 2
                )
            )

            Order.objects.filter(
                pk=order.pk
            ).update(
                created_at=order_date
            )

            StockMovement.objects.filter(
                order=order
            ).update(
                created_at=(
                    order_date
                    + timedelta(
                        minutes=15
                    )
                )
            )

    def _create_restock_movements(
        self,
        products,
        users,
    ):
        restocks = (
            (
                "KB-LOG-120",
                12,
                "Supplier restock",
                3,
            ),
            (
                "SSD-SAM-870",
                10,
                "Supplier delivery",
                2,
            ),
            (
                "NET-TPL-AX55",
                5,
                "Supplier restock",
                1,
            ),
        )

        now = timezone.now()

        for (
            sku,
            quantity,
            reason,
            days_ago,
        ) in restocks:
            product = products[
                sku
            ]["object"]

            register_stock_entry(
                product=product,
                quantity=quantity,
                reason=reason,
            )

            movement = (
                StockMovement.objects
                .filter(
                    product=product,
                    movement_type=(
                        StockMovement
                        .MovementType
                        .ENTRY
                    ),
                )
                .order_by("-pk")
                .first()
            )

            StockMovement.objects.filter(
                pk=movement.pk
            ).update(
                created_by=users[
                    "operator_2"
                ],
                created_at=(
                    now
                    - timedelta(
                        days=days_ago
                    )
                ),
            )

    def _create_draft_orders(
        self,
        products,
        users,
    ):
        definitions = (
            (
                "Mediterráneo Digital",
                (
                    ("MN-LG-27MR4", 3),
                    ("DOC-KEN-484", 2),
                ),
            ),
            (
                "Agencia Horizonte",
                (
                    ("KB-LOG-120", 6),
                    ("MS-LOG-203", 6),
                ),
            ),
            (
                "Studio Norte",
                (
                    ("PRN-EPS-2850", 2),
                    ("USB-SAN-128", 10),
                ),
            ),
            (
                "RedLink Consulting",
                (
                    ("NET-UBI-UX", 4),
                    ("NET-NET-GS8", 3),
                ),
            ),
            (
                "Pending Stock Customer",
                (
                    ("PRN-CAN-5350", 2),
                ),
            ),
        )

        now = timezone.now()

        for index, (
            customer,
            lines,
        ) in enumerate(definitions):
            order = create_order(
                customer_name=customer,
                notes=(
                    "Pending warehouse confirmation."
                ),
                created_by=users[
                    "operator_1"
                ],
            )

            for sku, quantity in lines:
                add_order_item(
                    order=order,
                    product=products[
                        sku
                    ]["object"],
                    quantity=quantity,
                )

            Order.objects.filter(
                pk=order.pk
            ).update(
                created_at=(
                    now
                    - timedelta(
                        days=index,
                        hours=3,
                    )
                )
            )

    def _create_cancelled_orders(
        self,
        products,
        users,
    ):
        definitions = (
            (
                "Cancelled Retail Project",
                (
                    ("KB-MS-600", 4),
                    ("MS-LOG-203", 2),
                ),
            ),
            (
                "Old Office Request",
                (
                    ("PRN-BRO-L24", 1),
                    ("UPS-APC-950", 1),
                ),
            ),
            (
                "North Coast Studio",
                (
                    ("CAM-LOG-C920", 2),
                ),
            ),
        )

        now = timezone.now()

        for index, (
            customer,
            lines,
        ) in enumerate(definitions):
            order = create_order(
                customer_name=customer,
                notes=(
                    "Cancelled before stock allocation."
                ),
                created_by=users[
                    "operator_2"
                ],
            )

            for sku, quantity in lines:
                add_order_item(
                    order=order,
                    product=products[
                        sku
                    ]["object"],
                    quantity=quantity,
                )

            cancel_order(
                order=order
            )

            Order.objects.filter(
                pk=order.pk
            ).update(
                created_at=(
                    now
                    - timedelta(
                        days=8 + index
                    )
                )
            )

    def _backdate_user_activity(
        self,
        users,
    ):
        now = timezone.now()

        User.objects.filter(
            pk=users["manager"].pk
        ).update(
            last_login=(
                now
                - timedelta(hours=4)
            )
        )

        User.objects.filter(
            pk=users["operator_1"].pk
        ).update(
            last_login=(
                now
                - timedelta(hours=1)
            )
        )

        User.objects.filter(
            pk=users["operator_2"].pk
        ).update(
            last_login=(
                now
                - timedelta(days=1)
            )
        )

    def _print_summary(self):
        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Showcase database created successfully."
            )
        )

        self.stdout.write("")

        self.stdout.write(
            f"Categories: {Category.objects.count()}"
        )

        self.stdout.write(
            f"Suppliers: {Supplier.objects.count()}"
        )

        self.stdout.write(
            f"Products: {Product.objects.count()}"
        )

        self.stdout.write(
            (
                "Users: "
                f"{User.objects.count()} "
                "(including preserved superuser)"
            )
        )

        self.stdout.write(
            f"Orders: {Order.objects.count()}"
        )

        self.stdout.write(
            (
                "Confirmed orders: "
                f"{Order.objects.filter(status='CONFIRMED').count()}"
            )
        )

        self.stdout.write(
            (
                "Draft orders: "
                f"{Order.objects.filter(status='DRAFT').count()}"
            )
        )

        self.stdout.write(
            (
                "Cancelled orders: "
                f"{Order.objects.filter(status='CANCELLED').count()}"
            )
        )

        self.stdout.write(
            (
                "Stock movements: "
                f"{StockMovement.objects.count()}"
            )
        )

        self.stdout.write("")

        self.stdout.write(
            "Showcase users:"
        )

        self.stdout.write(
            "  laura.manager"
        )

        self.stdout.write(
            "  david.warehouse"
        )

        self.stdout.write(
            "  marta.operations"
        )

        self.stdout.write(
            (
                "Password: "
                f"{self.DEMO_PASSWORD}"
            )
        )