import re
from difflib import get_close_matches
from app import create_app
from flask import render_template, request, redirect, session, flash
from app.models import User, Product
from app.vectorDb import chroma_products
from app.extensions import db
from app.validation import validate_name, validate_phone
app = create_app()

# products = [
#     {
#         "id": 1,
#         "name": "Laptop",
#         "price": 50000,
#         "category": "Electronics",
#         "image": "laptop.jpg"
#     },
#     {
#         "id": 2,
#         "name": "Mobile",
#         "price": 20000,
#         "category": "Electronics",
#         "image": "mobile.jpg"
#     },
#     {
#         "id": 3,
#         "name": "Shirt",
#         "price": 999,
#         "category": "Men",
#         "image": "shirt.jpg"
#     },
#     {
#         "id": 4,
#         "name": "Kurti",
#         "price": 799,
#         "category": "Women",
#         "image": "kurti.jpg"
#     },
#     {
#         "id": 5,
#         "name": "Watch",
#         "price": 1499,
#         "category": "Accessories",
#         "image": "watch.jpg"
#     },
#     {
#         "id": 6,
#         "name": "Saree",
#         "price": 2000,
#         "category": "Women",
#         "image": "saree.jpg"
#     }
# ]

cart = []
@app.route("/add-old-products")
def add_old_products():

    old_products = [
        Product(
            name="Laptop",
            price=50000,
            category="Electronics",
            image="laptop.jpg"
        ),
        Product(
            name="Mobile",
            price=20000,
            category="Electronics",
            image="mobile.jpg"
        ),
        Product(
            name="Shirt",
            price=999,
            category="Men",
            image="shirt.jpg"
        ),
        Product(
            name="Kurti",
            price=799,
            category="Women",
            image="kurti.jpg"
        ),
        Product(
            name="Watch",
            price=1499,
            category="Accessories",
            image="watch.jpg"
        ),
        Product(
            name="Saree",
            price=2000,
            category="Women",
            image="saree.jpg"
        )
    ]

    db.session.add_all(old_products)
    db.session.commit()

    return "Old products added successfully!"

@app.route("/admin-to-users-table")
def admin_to_users_table():
    # Create an admin user and add it to the users table
    admin_user = User(username="jaya", email="jaya@123.com", is_admin=True)
    admin_user.set_password("jaya@123")  # Set a password for the admin user
    # Add the admin user to the users table commit the changes to the database
    # from app.extensions import db
    # users.append(admin_user)
    db.session.add(admin_user)
    db.session.commit()
    return "Admin user added to the users table successfully!"

@app.route("/")
def login():
    if "logged_in" in session and session["logged_in"]:
        return redirect("/products")
    return render_template("login.html")

@app.route("/login", methods=["GET","POST"])
def login_user():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        user = User.authenticate(username, password)
        if user:
            #create a session for the user
            session["username"] = username
            session["logged_in"] = True
            session["is_admin"] = user.is_admin
            session["user_id"] = user.id
            return redirect("/products")
        else:
            return render_template("login.html", error="Invalid Username or Password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    #redirect with message to login page
    return redirect("/?message=Logged out successfully")

@app.route("/products")
def product_list():

    products = Product.query.all()
    cart_count = 0

    for item in cart:
        cart_count += item["quantity"]

    return render_template(
        "products.html",
        products=products,
        cart_count=cart_count
    )



@app.route("/add-product")
def add_product_page():
    return render_template("add_product.html")



@app.route("/add-product", methods=["POST"])
def add_product():
    name = request.form["name"]
    price = request.form["price"]
    category = request.form["category"]
    description = request.form["description"]
    image = request.files["image"]
  

    #Store image in static/images folder
    if "image" in request.files:
        image_file = request.files["image"]
        if image_file.filename != "":
            file_name = image_file.filename
            image_path = f"app/static/images/{file_name}"
            image_file.save(image_path)
            image = file_name

    product = Product(
        name=name,
        price=float(price),
        category=category,
        image=image,
        description=description
    )
    db.session.add(product)
    db.session.commit()

    # Store the committed product ID in the Chroma collection.
    chroma_products.insert_product({
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "description": product.description
    })

    flash("Product added successfully!", "success")
    session["notification_count"] = session.get("notification_count", 0) + 1
    notifications = session.get("notifications", [])

    notifications.append({
    "message": "Product added successfully!",
    "type": "success"
    })

    session["notifications"] = notifications[-10:]
    return redirect("/products")

@app.route("/product/search")
def product_search():
    query = request.args.get("query", "")
    if query:
        # Search in the chroma db collection for products
        results = chroma_products.search_products(query)
        product_ids = [result["id"] for result in results]
        products = Product.query.filter(Product.id.in_(product_ids)).all()
    else:
        products = Product.query.all()

    return render_template("products.html", products=products, query=query)

@app.route("/product/<int:product_id>")
def product_detail(product_id):

    product = Product.query.get_or_404(product_id)

    return render_template(
        "product_detail.html",
        product=product
    )



@app.route("/ai-chat", methods=["POST"])
def ai_chat():

    message = request.form.get("message", "").strip()

    if not message:
        return {
            "message": "Please enter a message.",
            "products": []
        }
    products = []

    import re

    # =========================
    # FIND BUDGET
    # =========================

    budget_match = re.search(
        r"(?:under|below|less than|upto|up to)\s*[₹rs\.]*\s*(\d+(?:,\d+)*)",
        message.lower()
    )

    budget = None
    min_price = None

    min_price_match = re.search(
        r"(?:over|above|more than)\s*[₹rs\.]*\s*(\d+(?:,\d+)*)",
        message.lower()
    )

    if min_price_match:
        min_price = float(
            min_price_match.group(1).replace(",", "")
        )

    if budget_match:
        budget = float(
            budget_match.group(1).replace(",", "")
        )


    # =========================
    # REMOVE BUDGET WORDS
    # =========================

    search_text = re.sub(
        r"(?:under|below|less than|upto|up to)\s*[₹rs\.]*\s*(\d+(?:,\d+)*)",
        "",
        message.lower()
    ).strip()

    # =========================
    # NATURAL LANGUAGE CATEGORY
    # =========================

    category_names = [
        "electronics",
        "kids",
        "women",
         "women's",
        "men",
        "men's",
        "accessories",
        "bags & backpacks"
    ]

    detected_category = None

    for category_name in category_names:
        if category_name in search_text:
            detected_category = category_name.replace("'s", "")
            break

    # Check spelling mistakes
    if not detected_category:

        words = search_text.split()

        stop_words = {
            "show", "me", "find", "i", "need", "a", "an",
            "the", "please", "give", "want", "some"
        }

        for word in words:

            if word in stop_words:
                continue

            if len(word) < 4:
                continue

            close_match = get_close_matches(
                word,
                category_names,
                n=1,
                cutoff=0.8
            )

            if close_match:
                detected_category = close_match[0].replace("'s", "")
                break
    # =========================
    # PRICE FILTER KEYWORDS
    # =========================

    cheapest = (
    "cheapest" in search_text
    or "lowest price" in search_text
    or "cheap" in search_text
    )

    expensive = (
    "most expensive" in search_text
    or "highest price" in search_text
    or "expensive" in search_text
    )

    # =========================
    # CATEGORY SEARCH
    # =========================

    if detected_category:

        category_products = Product.query.filter(
            db.func.lower(Product.category) == detected_category
        ).all()

        products = category_products
       

        # Cheapest product
        if cheapest:
            products = sorted(
                products,
                key=lambda product: float(product.price)
            )[:1]

        # Most expensive product
        elif expensive:
            products = sorted(
                products,
                key=lambda product: float(product.price),
                reverse=True
            )[:1]

    # =========================
    # SPELLING CORRECTION
    # =========================

    correct_category = get_close_matches(
        search_text,
        category_names,
        n=1,
        cutoff=0.7
    )

    if correct_category:
        detected_category = correct_category[0].replace("'s", "")   

    # =========================
    # BUDGET FILTER
    # =========================

    if budget is not None:
        products = [
            product
            for product in products
            if float(product.price) <= budget
        ]



    # =========================
    # MINIMUM PRICE FILTER
    # =========================

    if min_price is not None:
        products = [
            product
            for product in products
            if float(product.price) > min_price
        ]

        

    # =========================
    # CHROMA SEARCH
    # =========================
    if not detected_category:

        results = chroma_products.search_products(search_text)

        if not results:
            return {
                "message": "Sorry, I could not find a matching product.",
                "products": []
            }


        product_ids = [result["id"] for result in results]


    # =========================
    # DATABASE SEARCH
    # =========================
    if not detected_category:

        products = Product.query.filter(
            Product.id.in_(product_ids)
        ).all()


        if not products:
            return {
                "message": "Sorry, I could not find a matching product.",
                "products": []
            }



    # =========================
    # PRODUCT NAME FILTER
    # =========================

    if not detected_category:

        words = search_text.split()

        # Remove common words
        stop_words = {
            "show", "me", "find", "i", "need", "a", "an",
            "the", "please", "give", "want", "some"
        }

        words = [
            word.rstrip("s")
            for word in words
            if word not in stop_words
        ]

        # Correct product spelling
        all_products = Product.query.all()

        product_names = [
            product.name.lower()
            for product in all_products
        ]

        corrected_words = []

        for word in words:

            if len(word) < 4:
                corrected_words.append(word)
                continue

            close_product = get_close_matches(
                word,
                product_names,
                n=1,
                cutoff=0.7
            )

            if close_product:
                corrected_words.append(close_product[0])
            else:
                corrected_words.append(word)

        words = corrected_words

        filtered_products = []

        for product in products:

            product_name = product.name.lower()
            category = product.category.lower() if product.category else ""

            if any(
                word in product_name or word in category
                for word in words
            ):
                filtered_products.append(product)

        if filtered_products:
            products = filtered_products


    # =========================
    # BUDGET FILTER
    # =========================

    if budget is not None:

        products = [
            product
            for product in products
            if float(product.price) <= budget
        ]


    # =========================
    # MINIMUM PRICE FILTER
    # =========================

    if min_price is not None:

        products = [
            product
            for product in products
            if float(product.price) > min_price
        ]


    # =========================
    # NO RESULT
    # =========================

    if not products:
        return {
            "message": "Sorry, I could not find a product matching your requirements.",
            "products": []
        }


    # =========================
    # PRODUCT DATA
    # =========================

    product_data = []

    for product in products:

        product_data.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "image": product.image,
            "description": product.description
        })
    result_count = len(product_data)
    category_text = ""
    if detected_category:
        category_text = detected_category

    budget_text = ""

    if budget_match:
        budget_text = f" under ₹{budget_match.group(1)}"

    return {
        "message": f"I found {result_count} product{'s' if result_count != 1 else ''}{' in ' + category_text if category_text else ''}{budget_text} for you:",
        "products": product_data
    }

@app.route("/delete-product/<int:id>")
def delete_product(id):

    product = Product.query.get(id)

    if product:
        # Delete from ChromaDB first
        chroma_products.delete_product(product.id)

        # Delete from postgres database
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!", "success")
        session["notification_count"] = session.get("notification_count", 0) + 1

        notifications = session.get("notifications", [])

        notifications.append({
            "message": "Product deleted successfully!",
            "type": "success"
        })

        session["notifications"] = notifications[-10:]

    return redirect("/products")


@app.route("/edit/<int:id>")
def edit_product_page(id):

    product = Product.query.get(id)
    if product:
        return render_template("edit_product.html", product=product)

    return "Product not found"


@app.route("/edit/<int:id>", methods=["POST"])
def edit_product(id):

    product = Product.query.get(id)

    if product:

        product.name = request.form["name"]
        product.price = float(request.form["price"])
        product.category = request.form["category"]
        product.description = request.form["description"]

        # optional image update
        if "image" in request.files:
            image_file = request.files["image"]

            if image_file.filename != "":
                file_name = image_file.filename
                image_path = f"app/static/images/{file_name}"

                image_file.save(image_path)
                product.image = file_name

        db.session.commit()
        flash("Product updated successfully!", "success")
        session["notification_count"] = session.get("notification_count", 0) + 1

        notifications = session.get("notifications", [])

        notifications.append({
            "message": "Product updated successfully!",
            "type": "success"
        })

        session["notifications"] = notifications[-10:]

        # Update the product in ChromaDB
        chroma_products.update_product(
            product.id,
            {
                "name": product.name,
                "category": product.category,
                "description": product.description
            }
        )

        return redirect("/products")

    return "Product not found"




@app.route("/buy/<int:id>")
def buy_product(id):
    product = Product.query.get(id)
    if product:
        return render_template("buy.html", product=product)

    return "Product not found"


@app.route("/buy/<int:id>", methods=["POST"])
def buy_now(id):

    product = Product.query.get(id)

    if product:
        custmoer_name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]   
        quantity = int(request.form["quantity"])

        # validate name

        name_error = validate_name(custmoer_name)
        if name_error:
            return name_error

        # validate phone
        phone_error = validate_phone(phone)
        if phone_error:
            return phone_error
        total_price = product.price * quantity

        return render_template(
            "payment.html",
            product=product,
            customer_name=custmoer_name,
            phone=phone,
            address=address,
            quantity=quantity,
            total_price=total_price
        )
    return "Product not found"

        

@app.route("/payment/<int:id>", methods=["GET", "POST"])
def payment(id):

    product = Product.query.get(id)

    if product:

        if request.method == "GET":
            return render_template(
                "payment.html",
                product=product,
                quantity=1,
                total_price=product.price,
                customer_name="",
                phone="",
                address=""
            )

        payment_method = request.form.get("payment_method", "")

        return render_template(
            "success.html",
            product=product,
            customer_name=request.form.get("customer_name", ""),
            phone=request.form.get("phone", ""),
            address=request.form.get("address", ""),
            quantity=request.form.get("quantity", 1),
            total_price=request.form.get("total_price", product.price),
            payment_method=payment_method
        )

    return "Product not found"


@app.route("/cart-payment", methods=["GET", "POST"])
def cart_payment():

    if not cart:
        return redirect("/cart")

    total_price = 0
    total_items = 0

    for product in cart:

        total_price += int(product["price"]) * product["quantity"]

        total_items += product["quantity"]

    if request.method == "GET":

        return render_template(
            "cart_payment.html",
            cart=cart,
            total_items=total_items,
            total_price=total_price
        )

    payment_method = request.form.get("payment_method", "")
    ordered_cart = cart.copy()
    cart.clear()

    return render_template(
        "cart_success.html",
        cart=ordered_cart,
        total_items=total_items,
        total_price=total_price,
        payment_method=payment_method
    )

@app.route("/cart/<int:id>")
def add_to_cart(id):

    product = Product.query.get(id)

    if product:

        for item in cart:
            if item["id"] == id:
                item["quantity"] += 1
                return redirect("/cart")

        cart.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "image": product.image,
            "quantity": 1
        })

        return redirect("/cart")

    return "Product not found"

@app.route("/cart")
def view_cart():

    total_price = 0
    total_items = 0

    for product in cart:

        total_price += int(product["price"]) * product["quantity"]

        total_items += product["quantity"]

    return render_template(
        "cart.html",
        cart=cart,
        total_price=total_price,
        total_items=total_items
    )

@app.route("/cart-checkout")
def cart_checkout():
    cart = session.get("cart", [])

    if not cart:
        return redirect("/cart")

    total_price = 0
    total_items = 0

    for product in cart:

        total_price += int(product["price"]) * product["quantity"]

        total_items += product["quantity"]

    return render_template(
        "cart_checkout.html",
        cart=cart,
        total_price=total_price,
        total_items=total_items
    )

@app.route("/increase-cart/<int:id>")
def increase_cart(id):

    for product in cart:

        if product["id"] == id:
            product["quantity"] += 1
            break

    return redirect("/cart")

@app.route("/decrease-cart/<int:id>")
def decrease_cart(id):

    for product in cart:

        if product["id"] == id:

            if product["quantity"] > 1:
                product["quantity"] -= 1

            break

    return redirect("/cart")


@app.route("/remove-cart/<int:id>")
def remove_from_cart(id):

    for product in cart:

        if product["id"] == id:

            cart.remove(product)

            break

    return redirect("/cart")

@app.route("/ai-finder")
def ai_finder():
    return render_template("ai_finder.html")



if __name__ == "__main__":
    app.run(debug=True)