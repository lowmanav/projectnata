from django.views.decorators.csrf import csrf_exempt
import logging
from django.forms.models import model_to_dict
from django.http import JsonResponse
from cart.models import Cart, CartItem, CartState
from goods.models import Goods, Product
from django.db.models import ObjectDoesNotExist
from userprofile.models import User

from django.contrib.auth.decorators import login_required
import json

logger = logging.getLogger(__name__)


# @csrf_exempt
# def products(request):
#     # curl http://127.0.0.1:8000/api/v1/products/
#     if request.method == "GET":
#         products_list = {"products": []}
#         for item in Product.objects.all():
#             products_list["products"].append(
#                 model_to_dict(item, fields=["id",
#                                             "name",
#                                             "description",
#                                             "unit",
#                                             "photo_url"
#                                             ]))
#         return JsonResponse(products_list, content_type='application/json')
#     if request.method == "POST":
#         # curl -X POST \
#         #  --header "Content-Type: application/json" \
#         # --data '{"name": "test 1"}' \
#         # http://127.0.0.1:8000/api/v1/products/
#         try:
#             data = json.loads(request.body)
#             product = Product()
#             product.name = data["name"] if "name" in data else ""
#             product.description = data["description"] if "description" in data else ""
#             product.unit = data["unit"] if "unit" in data else ""
#             product.photo_url = data["photo_url"] if "photo_url" in data else ""
#             res = product.save()
#             logger.debug(res)
#         except Exception as e:
#             return JsonResponse(
#                 {
#                     "status": "Product is not created",
#                     "error": e
#                 },
#                 status=500)
#         return JsonResponse({"status": "SUCCESS"})
#
#
# @csrf_exempt
# def product_details(request, pk):
#     if request.method == "GET":
#         # curl http://127.0.0.1:8000/api/v1/products/3/
#         g = Product.objects.get(pk=pk)
#         return JsonResponse(model_to_dict(g, fields=["id",
#                                                      "name",
#                                                      "description",
#                                                      "unit",
#                                                      "photo_url"
#                                                      ]))
#     elif request.method == "POST":
#         # curl --header "Content-Type: application/json" \
#         # --request POST --data '{"name":"xyz"}' \
#         # http://127.0.0.1:8000/api/v1/products/3/
#         try:
#             data = json.loads(request.body)
#             g = Product.objects.get(pk=pk)
#             g.name = data.get("name", None)
#             g.save()
#         except goods.models.Product.DoesNotExist:
#             return JsonResponse({"status": "Items does not exists"}, status=500)
#         return JsonResponse({"status": "SUCCESS"})
#     elif request.method == "DELETE":
#         # curl --request DELETE http://127.0.0.1:8000/api/v1/products/3/
#         try:
#             Product.objects.get(pk=pk).delete()
#         except goods.models.Product.DoesNotExist:
#             return JsonResponse({"status": "Items does not exists"}, status=500)
#         return JsonResponse({"status": "SUCCESS"})


@login_required
def item_add_to_cart(request):
    data = json.loads(request.body)
    logger.debug("data: %s", data)
    try:
        goods_id = data.get("goods_id", None)
        quantity = data.get("quantity", None)
    except Exception as e:
        return JsonResponse({"status": "data items does not completed in request"}, status=500)
    if goods_id == None or quantity == None:
        return JsonResponse({"status": "data items does not completed in request"}, status=500)
    goods_id = int(goods_id)
    quantity = int(quantity)
    cart = None
    cart_id = request.session.get("cart_id", None)
    logger.debug("cart_item_add cart_id: %s, goods_id: %s, quantity: %s", cart_id, goods_id, quantity)

    try:
        cart = Cart.objects.get(pk=cart_id)
    except ObjectDoesNotExist as e:
        cart_id = None

    if not cart_id:
        cart = Cart(
            docStateId=CartState.objects.get(pk=0),
            userId=User.objects.get(pk=request.user.id),
            employeeUserId=User.objects.get(pk=request.user.id),
            comment="New order")
        cart.save()
        cart_id = cart.pk
        request.session["cart_id"] = cart_id

    goods = Goods.objects.get(pk=goods_id)
    price = goods.price

    try:
        cart_item = CartItem.objects.get(goodsId=goods_id, cartId=cart_id)
        cart_item.quantity += quantity
    except ObjectDoesNotExist as e:
        cart_item = None

    logger.debug("cart %s", cart)
    if not cart_item:
        cart_item = CartItem(
            cartId=cart,
            goodsId=goods,
            quantity=quantity,
            price=price
        )
        logger.debug("create cart_item")

    logger.debug("goods_id %s cart_item %s", goods_id, cart_item)
    cart_item.save()
    try:
        cart_items = CartItem.objects.filter(cartId=cart_id)

    except ObjectDoesNotExist as e:
        logger.debug("exception: %s", e)
        cart_items = None

    itemsCount = len(cart_items)
    request.session['itemsCount'] = itemsCount
    request.session['cart_id'] = cart_id
    return JsonResponse({'cart_id': cart_id, 'itemsCount': itemsCount})


@login_required
def cart_item_inc_dec(request, goods_id, quantity):
    cart_id = request.session.get("cart_id", None)
    logger.debug("cart_item_inc cart_id: %s, goodsId: %s, quantity: %s", cart_id, goods_id, quantity)
    if request.method == "POST":
        try:
            cart = Cart.objects.get(pk=cart_id)
        except ObjectDoesNotExist as e:
            logger.debug("exception: %s", e)
            cart = None
        logger.debug("cart: %s", cart)
        try:
            cart_items = CartItem.objects.filter(cartId=cart_id)
        except ObjectDoesNotExist as e:
            logger.debug("exception: %s", e)
            cart_items = None

        logger.debug("cart_item: %s", cart_items)
        full = 0
        item = 0
        logger.debug("goods_id: %s", goods_id)

        for i in range(len(cart_items)):
            cart_items[i].quantity = int(cart_items[i].quantity)
            product = Product.objects.get(name=cart_items[i].goodsId)
            logger.debug("cart_items[i].goodsId: %s", product.pk)
            if goods_id == product.pk:
                goods = Goods.objects.get(productId=product.pk)
                if quantity > goods.quantity:
                    quantity = goods.quantity
                if quantity < 0:
                    quantity = 0

                cart_items[i].quantity = quantity
                cart_items[i].save()
                item = cart_items[i].quantity * cart_items[i].price
            full = full + cart_items[i].quantity * cart_items[i].price
    logger.debug("out.full: %s, out.item: %s", full, item)
    return JsonResponse({'full': full, 'item': item, 'quantity': quantity})
