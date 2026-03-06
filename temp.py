class Solution:
    def checkOnesSegment(self, s: str) -> bool:
        prev = None
        onesInRow = 0
        for ch in s:
            if prev is not None:
                if prev == "1" and ch == "1":
                    if onesInRow == 0:
                        onesInRow = 1
                    else:
                        return False

            prev = ch

        return True if onesInRow == 1 else False

