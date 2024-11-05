import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm

def check_landing(obj_rct: pg.Rect) -> bool:
    return obj_rct.bottom >= HEIGHT

class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (-1, 0): img0,  # 左
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.jump_speed = -20 # ジャンプの高さ
        self.is_jumping = False
        self.hp = 100
        self.fall_speed = 5
        self.state = "normal"

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        左右で左右に移動
        上でジャンプ
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        # 水平方向の移動量を計算
        sum_mv = [0, 0]
        for k in [pg.K_LEFT, pg.K_RIGHT]:
            if key_lst[k]:
                sum_mv[0] += __class__.delta[k][0]

        # ジャンプの処理
        if not self.is_jumping and key_lst[pg.K_UP]:
            self.is_jumping = True
            self.fall_speed = self.jump_speed

        # 重力の適用
        if self.is_jumping:
            self.rect.move_ip(0, self.fall_speed)
            self.fall_speed += 0.5  # 重力加速度
            if self.rect.bottom >= HEIGHT:
                self.rect.bottom = HEIGHT
                self.is_jumping = False
                self.fall_speed = 0
        else:
            self.rect.bottom = min(self.rect.bottom, HEIGHT)

        # 水平方向の移動
        if sum_mv[0] != 0:
            self.rect.move_ip(self.speed * sum_mv[0], 0)
            self.dire = (sum_mv[0], 0)
            self.image = self.imgs[self.dire]

        # キャラクターの位置を画面内に制限
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT

        screen.blit(self.image, self.rect)

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Boss", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = 15  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 15

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()
        

class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: int):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.speed = 10
        self.size = 1.0
        self.dmg = 1
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, self.size)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Chargebeam(pg.sprite.Sprite):
    """
    チャージビームに関するクラス
    """
    def __init__(self, bird: Bird, f: int):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
             f：フレーム数
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.speed = 20
        self.size = 3.0
        self.dmg = 2
        self.life = 3

        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, self.size)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

        if check_bound(self.rect) != (True, True):
            self.kill

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Boss", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Boss(pg.sprite.Sprite):
    """
    敵(ボス)に関するクラス
    """ 
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load("fig/file8080.png"), 0, 2.0)
        self.rect = self.image.get_rect()
        self.rect.center = 700, 0
        self.vx, self.vy = 0, +6
        self.bound = HEIGHT-200  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.tmr = 0
        self.hp = 50 # 敵のHPの初期値
        
    def update(self):
        """
        敵をstateに基づき移動させる
        決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.hp <= 0: # hpが0になった時に、selfをkill
            self.kill()
        
        if self.rect.centery > self.bound and self.state=="down": # 停止位置行った時とstateがdawnだったら、yのスピードを0に、stateをstop_dにする
            self.vy = 0
            self.state = "stop_d"
            
        if self.state == "stop_d": # stateの状態がstop_dの時、タイマーを＋1していく
            self.tmr += 1
            if self.tmr%20 == 0: # タイマーが20秒おきにstateをmoveに変えて、タイマーを初期化、vxを左方向へ
                self.state = "move"
                self.tmr = 0
                self.vx = -6
                
            else: # それ以外なら、止まる
                self.vx = 0

        if self.state == "stop": # stateがstopの時に、タイマーを+1していき、止まる
            self.tmr += 1
            self.vx = 0
            if self.tmr%20 == 0: # タイマーが20秒おきにstateをmoveに変えて、タイマーを初期化、vxを右方向へ
                self.state = "move"
                self.tmr = 0
                self.vx = 6

        if self.rect.centerx < 100: # self.rect.centerxが100より小さい時に、反転し、stateをstopに変える
            self.vx *= -1
            self.state = "stop"
            
        if self.rect.centerx > 1000: # self.rect.centerxが1000より大きい時に、反転し、stateをstop_dに変える
            self.vx *= -1
            self.state = "stop_d"
        
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Chargejudge:
    """
    チャージが完了しているか表示するクラス
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0  # フレーム数
        self.image = self.font.render("Charge:Hold SPACE", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 900, HEIGHT-50

    def update(self, screen: pg.Surface):
        if self.value >= 60:  # フレーム数が60以上だったら
            self.image = self.font.render("Charge 100%", 0, self.color)
        elif 10 <= self.value < 60:  # フレーム数が10以上60未満だったら
            self.image = self.font.render(f"Charging…{int(self.value/60*100)}%", 0, self.color)
        else:
            self.image = self.font.render("Charge:Hold SPACE", 0, self.color)
        screen.blit(self.image, self.rect)

class Hpbar:
    """
    HPバーを表示するクラス
    """
    def __init__(self, obj:Bird):
        self.obj = obj
        self.max = self.obj.hp  # HPの初期値を取得

    def update(self, screen:pg.Surface):
        diff = (self.max - self.obj.hp)
        # 画面左側にHPバーを描画
        pg.draw.rect(screen, (255, 0, 0), (20, 20, 20, self.max*2))
        pg.draw.rect(screen, (0, 255, 0), (20, 20 + 2 * diff, 20, self.obj.hp*2))
        pg.draw.rect(screen, (125, 50, 50), (20, 20, 20, self.max*2), 1)
        for i in range(self.max//2):
            pg.draw.rect(screen, (125, 50, 50), (20, 215-i*4, 20, 2), 1)

class HealItem(pg.sprite.Sprite):
    """
    回復アイテムに関するクラス
    """
    def __init__(self):
        """
        回復アイテムをランダムなx座標の画面上端に生成する
        大きさと回復量と落下速度が比例していて、その値はランダムで決まる（5段階）
        """
        super().__init__()
        self.random_num = random.randint(1, 5)
        self.heal_num = self.random_num*10
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/0.png"), 0, 0.5+(self.random_num/10))
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, 1 + self.random_num/2

    def update(self):
        """
        回復アイテムを速度ベクトルself.vyに基づき反転させながら落下させる
        画面端に到達したらself.kill()でインスタンスを削除する
        """
        if self.rect.centery/10%2 == 0:
            self.image = pg.transform.flip(self.image, True, False)
        if self.rect.centery > HEIGHT:
            self.kill()
        self.rect.move_ip(self.vx, self.vy)

    def heal(self, bird: Bird):
        """
        Birdクラスのhpを回復量分回復する関数
        """
        mx_hp = 100
        if (self.heal_num+bird.hp) <= mx_hp:
            bird.hp += self.heal_num
        else:
            bird.hp = mx_hp

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/stage3.png")
    score = Score()
    c_judge = Chargejudge()

    bird = Bird(3, (WIDTH/4, HEIGHT))
    hpbar = Hpbar(bird)
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    c_beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    healitems = pg.sprite.Group()

    tmr = 0
    i_tmr = 0
    judge = False  # チャージしているか判定する。初期値False
    clock = pg.time.Clock()

    emys.add(Boss()) # 敵の呼び出し

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE: # スペースを押したら
                judge = True
                c_tmr = 0  # チャージのタイマーを定義。初期値0
            if event.type == pg.KEYUP and event.key == pg.K_SPACE:  # スペースを離したら
                if c_tmr >= 60:  # 60以上なら
                    c_beams.add(Chargebeam(bird, c_tmr))  # Chargebeamクラスに送る
                else:
                    beams.add(Beam(bird, 0))  # Beamクラスに送る
                judge = False

        screen.blit(bg_img, [0, 0])
        
        if len(emys) == 0:  
            bird.change_img(9, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        if judge:  # judgeがTrueなら
            c_tmr += 1  # チャージのタイマーをカウントし、Chargejudgeクラスのvalueに送る
            c_judge.value = c_tmr
        else:
            c_judge.value = 0

        if tmr%100 == 0:  # 100フレームに一回乱数を発生させる
            r_num = random.randint(1, 5)
            if r_num == 1:  # 1/5の確率でアイテムを出現させる
                healitems.add(HealItem())

        for emy in emys:
            if tmr%30 == 0 and emy.state != "down":
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))
            
        for emy in pg.sprite.spritecollide(bird, emys, False):
            if bird.state != "invincible":
                bird.hp -= 10
                bird.change_img(4, screen)  # こうかとんダメージリアクション 
                bird.state = "invincible"
                i_tmr = 60

            if bird.hp <= 0:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                pg.display.update()
                time.sleep(2)
                return
            
        i_tmr -= 1
        if i_tmr < 0:
            bird.state = "normal"

        for emy in pg.sprite.groupcollide(emys, beams, False, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            emy.hp -= 1
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for emy in pg.sprite.groupcollide(emys, c_beams, False, True).keys():  # 敵とチャージビームの衝突
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            emy.hp -= 5
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.groupcollide(bombs, c_beams, True, False).keys():  # 爆弾とチャージビームの衝突。チャージビームは衝突時に消えない
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
            score.update(screen)
            bird.change_img(4, screen)  # こうかとんダメージリアクション 
            bird.hp -= 10
            if bird.hp <= 0:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                pg.display.update()
                time.sleep(2)
                return
        
        elif len(pg.sprite.spritecollide(bird, healitems, True)) != 0:  # アイテムとこうかとんとの衝突判定
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
            if (10+bird.hp) <= 100:
                bird.hp += 10
            else:
                bird.hp = 100 
            
            pg.display.update()
            time.sleep(0.1)  # 0.1秒停止

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        c_beams.update()
        c_beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        c_judge.update(screen)
        healitems.update()  # 回復アイテムの位置更新
        healitems.draw(screen)  # 回復アイテムの描画
        hpbar.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit() 
    sys.exit()