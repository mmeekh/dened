class Background {
    constructor(canvas) {
        this.canvas = canvas;
        this.width = canvas.width;
        this.height = canvas.height;
        
        // Scroll speed
        this.speed = 0.5;
        
        // Background positions for parallax effect
        this.skyPos = 0;
        this.groundPos = 0;
        this.cloudPos = 0;
        
        // Create cloud positions
        this.clouds = [];
        for (let i = 0; i < 3; i++) {
            this.clouds.push({
                x: Math.random() * this.width,
                y: Math.random() * 100 + 20,
                width: Math.random() * 60 + 40,
                speed: Math.random() * 0.3 + 0.2
            });
        }
    }
    
    update() {
        // Update positions for scrolling effect
        this.groundPos = (this.groundPos + this.speed) % this.width;
        this.cloudPos = (this.cloudPos + this.speed * 0.3) % this.width;
        
        // Update cloud positions
        for (let cloud of this.clouds) {
            cloud.x -= cloud.speed;
            if (cloud.x + cloud.width < 0) {
                cloud.x = this.width;
                cloud.y = Math.random() * 100 + 20;
            }
        }
    }
    
    draw(ctx) {
        // Draw sky gradient
        const skyGradient = ctx.createLinearGradient(0, 0, 0, this.height);
        skyGradient.addColorStop(0, '#87CEEB');  // Light blue at top
        skyGradient.addColorStop(1, '#E0F7FF');  // Lighter blue at bottom
        ctx.fillStyle = skyGradient;
        ctx.fillRect(0, 0, this.width, this.height);
        
        // Draw clouds
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        for (let cloud of this.clouds) {
            ctx.beginPath();
            ctx.arc(cloud.x, cloud.y, cloud.width/2, 0, Math.PI * 2);
            ctx.arc(cloud.x + cloud.width * 0.4, cloud.y - cloud.width * 0.1, cloud.width/2, 0, Math.PI * 2);
            ctx.arc(cloud.x + cloud.width * 0.2, cloud.y + cloud.width * 0.1, cloud.width/2, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Draw distant mountains
        const mountainHeight = this.height * 0.3;
        ctx.fillStyle = '#8B7355';  // Brown color for mountains
        ctx.beginPath();
        ctx.moveTo(0, this.height - mountainHeight - 20);
        
        // Create a jagged mountain range
        for (let x = 0; x < this.width; x += 50) {
            const height = Math.sin(x * 0.02) * 30 + mountainHeight;
            ctx.lineTo(x, this.height - height - 20);
        }
        
        ctx.lineTo(this.width, this.height - 20);
        ctx.lineTo(0, this.height - 20);
        ctx.fill();
        
        // Draw ground
        const groundHeight = 20;
        
        // Draw ground base
        ctx.fillStyle = '#8B4513';  // Brown
        ctx.fillRect(0, this.height - groundHeight, this.width, groundHeight);
        
        // Draw grass on top
        ctx.fillStyle = '#7CFC00';  // Light green
        ctx.fillRect(0, this.height - groundHeight, this.width, 5);
        
        // Draw ground details - repeating pattern
        ctx.fillStyle = '#9B5613';  // Darker brown for details
        for (let x = -this.groundPos; x < this.width; x += 30) {
            ctx.fillRect(x, this.height - groundHeight + 8, 15, 4);
        }
        
        this.update();
    }
}