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


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
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
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.hp = 100  # HP初期値設定

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
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
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
        rad = random.randint(30, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

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
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/alien1.png"),0, 2.0) # 敵の写真をロード
        self.rect = self.image.get_rect()
        self.rect.center = 700, 0
        self.vx, self.vy = 0, +6
        self.bound = HEIGHT-200  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.tmr = 0
        self.hp = 5 # 敵のHPの初期値
        

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

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    c_judge = Chargejudge()

    bird = Bird(3, (900, 400))
    hpbar = Hpbar(bird)
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    c_beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()

    

    tmr = 0
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

        for emy in emys:
            if emy.state != "down" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))
            
        for emy in pg.sprite.spritecollide(bird, emys, False):
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return 

        for emy in pg.sprite.groupcollide(emys, beams, False, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            emy.hp -= 1
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for emy in pg.sprite.groupcollide(emys, c_beams, True, True).keys():  # 敵とチャージビームの衝突
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.groupcollide(bombs, c_beams, True, False).keys():  # 爆弾とチャージビームの衝突。チャージビームは衝突時に消えない
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
            bird.change_img(8, screen) # こうかとん喜びエフェクト
            score.update(screen)
            bird.change_img(4, screen)  # こうかとんダメージリアクション 
            bird.hp -= 10
            if bird.hp <= 0:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                pg.display.update()
                time.sleep(2)
                return

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
        hpbar.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)

    
        
        


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit() 
    sys.exit()