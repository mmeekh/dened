// Character image using your Imgur image
const characterImage = new Image();
// Direct link to your Imgur image
characterImage.src = 'https://i.imgur.com/SexZx07.png';

// Debug logs to verify image loading
console.log("Character image loading from Imgur...");
characterImage.onload = function() {
    console.log("✅ Character image loaded successfully from Imgur!");
};
characterImage.onerror = function() {
    console.error("❌ Character image failed to load from Imgur");
    // Fallback to a simpler URL in case of error
    console.log("Trying fallback image URL...");
    this.src = 'https://i.imgur.com/SexZx07.png';
};

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;  // Görselin genişliği
        this.height = 40; // Görselin yüksekliği
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        // Görselin yüklenmesi için hazırlık
        this.image = characterImage;
    }
    
    update() {
        this.velocity += this.gravity;
        if (this.velocity > 2.0) {
            this.velocity = 2.0;
        }
        
        this.floatOffset += this.floatSpeed;
        let floatEffect = Math.sin(this.floatOffset) * 0.3;
        this.y += this.velocity + floatEffect;
        
        if (this.y - this.height/2 < 0) {
            this.y = this.height/2;
            this.velocity = 0;
        }
        
        if (this.y + this.height/2 > this.canvas.height - 20) {
            this.y = this.canvas.height - 20 - this.height/2;
            this.velocity = 0;
            return true;
        }
        return false;
    }
    
    draw(ctx) {
        ctx.save(); // Mevcut çizim durumunu kaydet
        
        // Karakterin hareketi için açı hesaplama
        let angle = 0;
        if (this.velocity < 0) {
            // Yukarı doğru hareket ederken hafif yukarı bak
            angle = -Math.PI/15; // Yaklaşık -12 derece
        } else if (this.velocity > 1) {
            angle = Math.PI/15; // Yaklaşık 12 derece
        }
        
        ctx.translate(this.x, this.y);
        ctx.rotate(angle);
        
        // Draw the character image with error handling
        if (this.image.complete && this.image.naturalHeight !== 0) {
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
        } else {
            // Fallback drawing in case image is still loading
            this.drawFallbackCharacter(ctx);
        }
        
        ctx.restore(); // Çizim durumunu geri yükle
    }
    
    // Fallback drawing method
    drawFallbackCharacter(ctx) {
        // Simple character while image loads
        ctx.fillStyle = '#44A244';
        ctx.beginPath();
        ctx.ellipse(0, 0, this.width/2, this.height/2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = '#2E7D32';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-this.width/3, 0);
        ctx.lineTo(this.width/3, 0);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, -this.height/3);
        ctx.lineTo(0, this.height/3);
        ctx.stroke();
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