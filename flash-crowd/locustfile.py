from locust import HttpUser, task, between
import random

class Shopper(HttpUser):
    # Simulate human think-time between actions (2 to 9 seconds)
    wait_time = between(2, 9)

    def on_start(self):
        # Land on the catalogue
        self.client.get("/")

    @task
    def browse_and_view(self):
        # Browse a few catalogue pages (power-law-ish depth)
        for _ in range(random.choice([1, 1, 2, 2, 3, 5])):
            self.client.get("/", name="/catalogue")
            
        # Pick a product (Product 1 is our "viral" item from the DB seed)
        pid = random.randint(1, 3)
        
        # Open the expensive product page
        self.client.get(f"/product/{pid}", name="/product/[id]")
        
        # Fetch the page's sub-resources, exactly like a real browser
        for asset in ["/static/app.css", "/static/app.js", f"/img/product_{pid}.jpg"]:
            self.client.get(asset, name="/static")
            
        # Dwell is automatically handled by the wait_time before the next task loop,
        # but we simulate the cart decision here.
        if random.random() < 0.15:
            # 15% chance to actually complete the task
            self.client.post("/checkout", json={"product": pid}, name="/checkout")