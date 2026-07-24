

from enum import unique, Enum, EnumMeta

class EnumDirectValueMeta(EnumMeta):
    def __getattribute__(cls, name):
        value = super().__getattribute__(name)
        if isinstance(value, cls):
            value = value.value
        return value

class videoMarks():

    def __init__(self):
        super().__init__()

        self._markQualityMap = dict()
        for mark__, quality__ in self._markQualEnum.__members__.items():
            self._markQualityMap[mark__[1:]] = quality__

        #for key_ in self.markQualityMap :
            #print(f"mark=={key_}::quality=={self.markQualityMap[key_]}")


        self._qualityResMap = dict()
        for quality__, resolution__ in self._qualResEnum.__members__.items():
            self._qualityResMap[quality__[1:]] = resolution__

        #for key_ in self._qualityResMap :
            #print(f"quality=={key_}::resolution=={self._qualityResMap[key_]}")




    def getQuality4romMark(self, mark__: str) -> str :
        key_obj = self._markQualityMap.get(mark__)
        return key_obj.value if key_obj else ""

    def getRes4romQuality(self, qual__: str) -> str :
        key_obj = self._qualityResMap.get(qual__)
        return key_obj.value if key_obj else ""

    def getQuality4romRes(self, res__: str) -> str :
        try :
            key_obj = self._qualResEnum(res__)
            return key_obj.name[1:]
        except ValueError :
            pass
        return ""
    

    class _markQualEnum(str, Enum, metaclass=EnumDirectValueMeta):
        _144p   = "144p"
        _240p   = "240p"
        _360p   = "360p"
        _480p   = "480p"
        _SD     = _480p  # reference mark/synonymous name of quality standard
        _sd     = _480p
        _720p   = "720p"
        _HD     = _720p
        _hd     = _720p
        _1080p  = "1080p"
        _FULLHD = _1080p
        _FullHD = _1080p
        _fullHD = _1080p
        _fullhd = _1080p
        _1440p  = "1440p"
        _2K     = _1440p
        _2k     = _1440p
        _2160p  = "2160p"
        _4K     = _2160p
        _4k     = _2160p
        _2880p  = "2880p"
        _5K     = _2880p
        _5k     = _2880p
        _4320p  = "4320p"
        _8K     = _4320p
        _8k     = _4320p

    # NTSC widescreen quals standard (Used on Youtube)
    @unique 
    class _qualResEnum(str, Enum, metaclass=EnumDirectValueMeta):
        _144p  = "256x144"#_256x144   = "144p"
        _240p  = "426x240"#_426x240   = "240p"
        _360p  = "640x360"#_640x360   = "360p"
        _480p  = "854x480"#_854x480   = "480p"
        _720p  = "1280x720"#_1280x720  = "720p"
        _1080p = "1920x1080"#_1920x1080 = "1080p"
        _1440p = "2560x1440"#_2560x1440 = "1440p"
        _2160p = "3840x2160"#_3840x2160 = "2160p"
        _2880p = "5120x2880"#_5120x2880 = "2880p"
        _4320p = "7680x4320"#_7680x4320 = "4320p"


    def get_closest_qual(self, qual: str, qualityList = None) -> str:
        if qualityList is None:
            qualityList = [x.value for x in self._qualityResMap.values()]#list(map(lambda x: x.value, self._qualityResMap.values()))

        print("map type==", type(qualityList))
        print("map==", qualityList)
        

        if qual in qualityList :
            print(qual, " in enum!!")
            return qual
        #return ""


        split = qual.split('x')[-1]
        if split == qual:
            return ""

        qual_height = int(split)

        qual_heights = [int(el.split('x')[-1]) for el in qualityList]

        ind, val = min(enumerate(qual_heights), key=lambda x:abs(x[1] - qual_height))
        #print("ind==", ind, "val==", val)

        #return list(qualityList)[ind].value
        return qualityList[ind]


if __name__ == "__main__":
    marks = videoMarks()
    print("getQual4Mark==", marks.getQuality4romMark("FullHD"))
    print("getQual4Mark==", marks.getQuality4romMark("HDgsdfgg"))
    print("getQual4Mark==", marks.getQuality4romMark(""))
    print("getQual4Mark==", marks.getQuality4romMark("-1"))

    print("qual4res==", marks.getQuality4romRes("1280x720"))
    print("qual4res==", marks.getQuality4romRes("1280x72"))
    print("qual4res==", marks.getQuality4romRes(""))
    print("qual4res==", marks.getQuality4romRes("-1"))
    print("qual4res==", marks.getQuality4romRes("abc"))

    print("res4qual(enum)==", marks.getRes4romQuality("144p"))
    print("res4qual(enum)==", marks.getRes4romQuality("720"))
    print("res4qual(enum)==", marks.getRes4romQuality(""))
    print("res4qual(enum)==", marks.getRes4romQuality("-1"))
    print("res4qual(enum)==", marks.getRes4romQuality("abc"))

    lis = ["256x144", "424x240", "492x360", "856x480"]

    res = marks.get_closest_qual(marks.getRes4romQuality(marks.getQuality4romMark("HD")), lis)
    print("fin==", res)
    #print("fin2==", marks.getQuality4romRes(res))



