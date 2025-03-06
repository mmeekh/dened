// Karakter görseli
const characterImage = new Image();
characterImage.src = 'Static/Assets/flappy-character.png'; // Capital "A" in Assets

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
        
        // Add error handling for image
        this.imageLoaded = false;
        this.image.onload = () => {
            console.log("Character image loaded successfully!");
            this.imageLoaded = true;
        };
        this.image.onerror = () => {
            console.error("Failed to load character image:", this.image.src);
            this.imageLoaded = false;
        };
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
        
        if (this.imageLoaded) {
            // If image loaded successfully, draw the image
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
        } else {
            // Fallback: Draw a simple weed if image fails to load
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
        
        ctx.restore(); // Çizim durumunu geri yükle
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