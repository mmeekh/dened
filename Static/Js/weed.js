class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;
        this.height = 40;
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
    }

    update() {
        // Update logic remains the same
    }

    draw(ctx) {
        ctx.save(); // Save current state

        // Calculate angle based on velocity for rotation
        let angle = 0;
        if (this.velocity < 0) {
            angle = -Math.PI / 15; // About -12 degrees
        } else if (this.velocity > 1) {
            angle = Math.PI / 15; // About 12 degrees
        }

        ctx.translate(this.x, this.y);
        ctx.rotate(angle);

        // Draw the marijuana leaf
        ctx.fillStyle = '#44A244'; // Green color for the leaf
        ctx.strokeStyle = '#2E7D32'; // Darker green for the veins
        ctx.lineWidth = 2;

        // Main leaf shape (serrated edges)
        ctx.beginPath();
        ctx.moveTo(-this.width / 2, 0); // Start from the left middle
        ctx.lineTo(-this.width / 3, -this.height / 3); // Top-left serration
        ctx.lineTo(0, -this.height / 2); // Top center
        ctx.lineTo(this.width / 3, -this.height / 3); // Top-right serration
        ctx.lineTo(this.width / 2, 0); // Right middle
        ctx.lineTo(this.width / 3, this.height / 3); // Bottom-right serration
        ctx.lineTo(0, this.height / 2); // Bottom center
        ctx.lineTo(-this.width / 3, this.height / 3); // Bottom-left serration
        ctx.closePath(); // Close the path to complete the shape
        ctx.fill(); // Fill the leaf with green color
        ctx.stroke(); // Draw the outline

        // Draw veins (more detailed)
        ctx.beginPath();
        ctx.moveTo(-this.width / 2, 0); // Left middle
        ctx.lineTo(0, -this.height / 2); // Top center
        ctx.moveTo(-this.width / 2, 0); // Left middle
        ctx.lineTo(0, this.height / 2); // Bottom center
        ctx.moveTo(this.width / 2, 0); // Right middle
        ctx.lineTo(0, -this.height / 2); // Top center
        ctx.moveTo(this.width / 2, 0); // Right middle
        ctx.lineTo(0, this.height / 2); // Bottom center
        ctx.stroke();

        // Add smaller veins for realism
        ctx.beginPath();
        ctx.moveTo(-this.width / 3, -this.height / 3); // Top-left serration
        ctx.lineTo(0, -this.height / 4); // Mid-top
        ctx.moveTo(this.width / 3, -this.height / 3); // Top-right serration
        ctx.lineTo(0, -this.height / 4); // Mid-top
        ctx.moveTo(-this.width / 3, this.height / 3); // Bottom-left serration
        ctx.lineTo(0, this.height / 4); // Mid-bottom
        ctx.moveTo(this.width / 3, this.height / 3); // Bottom-right serration
        ctx.lineTo(0, this.height / 4); // Mid-bottom
        ctx.stroke();

        // Add texture (small dots for realism)
        ctx.fillStyle = '#388E3C'; // Slightly darker green
        for (let i = 0; i < 20; i++) {
            let x = (Math.random() - 0.5) * this.width; // Random x position within leaf
            let y = (Math.random() - 0.5) * this.height; // Random y position within leaf
            ctx.beginPath();
            ctx.arc(x, y, 1, 0, Math.PI * 2); // Small dots
            ctx.fill();
        }

        ctx.restore(); // Restore state
    }

    jump() {
        this.velocity = -3.8;
        game.sound.play('jump');
    }

    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}