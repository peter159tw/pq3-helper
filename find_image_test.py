from actions import find_images
import cv2
from log.logger import Logger

log = Logger()
#img = cv2.imread("/Users/petershih/Documents/pq3-helper/_temp_last_screenshot.png")
img = cv2.imread("/Users/petershih/Documents/pq3-helper/actions/enemy_status_stunned/score_0.03_1627265781.0164962.png")
cv2.imshow("screenshot", img)
ret = find_images.find_image("enemy_status_stunned", img, log)
#ret = find_images.find_image("battle_waiting_action", img, log)

print(ret)

cv2.waitKey()
cv2.destroyAllWindows()