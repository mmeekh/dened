// Game.html içindeki script bölümünde karakter sınıfı güncellemesi

// Karakter görüntüsünü yükle
const characterImage = new Image();
// Not: URL'yi düzeltin - aşağıdaki URL sadece bir örnek, doğru URL'nizi kullanın
characterImage.src = 'https://i.ibb.co/N2rvrqm/flappy-character.png'; 

console.log("Karakter görüntüsü yükleniyor...");
characterImage.onload = function() {
    console.log("✅ Karakter görüntüsü başarıyla yüklendi!");
};
characterImage.onerror = function() {
    console.error("❌ Karakter görüntüsü yüklenemedi!");
    console.log("URL'yi kontrol edin ve doğru olduğundan emin olun");
    // Yedek görüntü için varsayılan çizimi kullanacak
};

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 50;  // Görüntü genişliği
        this.height = 50; // Görüntü yüksekliği
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        // Görüntüyü kullan
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
        
        // Görüntüyü kontrol et ve çiz
        if (this.image.complete && this.image.naturalHeight !== 0) {
            // Görüntü yüklendiyse çiz
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
            
            // Hata ayıklama için (isteğe bağlı) - görüntü sınırlarını göster
            // ctx.strokeStyle = 'red';
            // ctx.strokeRect(-this.width/2, -this.height/2, this.width, this.height);
        } else {
            // Görüntü yoksa yedek çizim yap
            this.drawFallbackCharacter(ctx);
        }
        
        ctx.restore(); // Çizim durumunu geri yükle
    }
    
    // Yedek çizim metodu
    drawFallbackCharacter(ctx) {
        // Basit karakter çizimi
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
        playSound('jump'); 
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}