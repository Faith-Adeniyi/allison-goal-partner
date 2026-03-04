import os
from PIL import Image, ImageDraw, ImageFont

class CelebrationEngine:
    def __init__(self):
        # Professional setup: Ensure the output directory exists
        self.output_dir = "celebrations"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_milestone_card(self, user_name, milestone_text, frequency):
        """
        Generates a 1080x1080 (Square) static card for social sharing.
        Suitable for WhatsApp, Instagram, or Device Download.
        """
        width, height = 1080, 1080
        background_color = (45, 10, 85) # Deep Allison Purple
        card = Image.new('RGB', (width, height), color=background_color)
        draw = ImageDraw.Draw(card)

        # Neon Green accent border for energy
        draw.rectangle([20, 20, 1060, 1060], outline=(0, 255, 150), width=15) 

        # Placeholder for font - using default for system compatibility
        # RED: REPLACE WITH ImageFont.truetype("arial.ttf", size) FOR CUSTOM FONTS
        font = ImageFont.load_default()

        # Center-aligned Hype Text
        draw.text((width//2, 200), "MILESTONE ACHIEVED!", fill=(0, 255, 150), anchor="mm")
        draw.text((width//2, 450), f"Great job, {user_name}!", fill=(255, 255, 255), anchor="mm")
        draw.text((width//2, 600), f"COMPLETED: {milestone_text}", fill=(255, 215, 0), anchor="mm") 
        draw.text((width//2, 850), f"YOUR {frequency.upper()} WIN", fill=(200, 200, 200), anchor="mm")

        file_name = f"milestone_{user_name.replace(' ', '_')}.png"
        file_path = os.path.join(self.output_dir, file_name)
        card.save(file_path)
        
        return file_path

    def create_grand_finale_gif(self, user_name, goal_name):
        """
        Generates an animated GIF with flashing vibrant colors for the grand finale.
        This represents the 'Exciting' celebration your boss requested.
        """
        width, height = 1080, 1080
        frames = []
        
        # Define a sequence of celebratory colors
        vibrant_colors = [
            (45, 10, 85),   # Purple
            (0, 150, 255),  # Electric Blue
            (255, 20, 147), # Deep Pink
            (0, 200, 100)   # Emerald
        ]

        # Generate 10 frames with alternating colors and sizes
        for i in range(10):
            bg_color = vibrant_colors[i % len(vibrant_colors)]
            frame = Image.new('RGB', (width, height), color=bg_color)
            draw = ImageDraw.Draw(frame)
            
            # Flashing border
            border_color = vibrant_colors[(i + 1) % len(vibrant_colors)]
            draw.rectangle([30, 30, 1050, 1050], outline=border_color, width=25)

            # Victory Text
            draw.text((width//2, 300), "🏆 GOAL CRUSHED! 🏆", fill=(255, 255, 255), anchor="mm")
            draw.text((width//2, 540), f"CONGRATULATIONS {user_name.upper()}", fill=(255, 215, 0), anchor="mm")
            draw.text((width//2, 700), f"TOTAL ACHIEVEMENT: {goal_name}", fill=(255, 255, 255), anchor="mm")
            
            frames.append(frame)

        # Save as an animated GIF
        file_name = f"GRAND_FINALE_{user_name.replace(' ', '_')}.gif"
        file_path = os.path.join(self.output_dir, file_name)
        
        frames[0].save(
            file_path,
            save_all=True,
            append_images=frames[1:],
            duration=200,  # 200ms per frame
            loop=0         # Loop forever
        )
        
        return file_path