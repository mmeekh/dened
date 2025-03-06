// Karakter görseli
const characterImage = new Image();
characterImage.src = 'Static/assets/flappy-character.png';

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
        
        ctx.drawImage(
            this.image, 
            -this.width/2, 
            -this.height/2, 
            this.width, 
            this.height
        );
        
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