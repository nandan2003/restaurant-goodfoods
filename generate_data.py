import pandas as pd
from faker import Faker
import random

# Initialize Faker
fake = Faker()

# Define possible values for restaurant attributes
CUISINES =
PRICE_RANGES = ['$', '$$', '$$$']
SPECIAL_TAGS = ['outdoor_seating', 'live_music', 'family_friendly', 'romantic', 'rooftop_bar', 'pet_friendly', 'good_for_groups', 'quiet']

def generate_restaurant_data(num_records=100):
    """
    Generates a synthetic dataset of restaurant locations.
    """
    data =
    for i in range(1, num_records + 1):
        name = f"{fake.company()} Bistro"
        city = fake.city()
        address = fake.street_address()
        cuisine = random.choice(CUISINES)
        capacity = random.randint(20, 150)
        price = random.choice(PRICE_RANGES)
        
        # Generate a few special tags for each restaurant
        num_tags = random.randint(1, 4)
        tags = ','.join(random.sample(SPECIAL_TAGS, num_tags))

        data.append({
            'id': i,
            'name': name,
            'location_city': city,
            'address': address,
            'cuisine': cuisine,
            'seating_capacity': capacity,
            'price_range': price,
            'special_tags': tags
        })
        
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    restaurant_df = generate_restaurant_data(100)
    restaurant_df.to_csv('restaurants.csv', index=False)
    print("Successfully generated restaurants.csv with 100 records.")


