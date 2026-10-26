from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FacilitySource:
    key: str
    name_zh: str
    dataset_id: str
    research_record_count: int
    research_checked_on: str = "2026-10-22"
    count_provenance: str = "user_supplied_research"
    default_sport: str | None = None
    category: str | None = None

    @property
    def category_key(self) -> str:
        return self.category or self.key

    @property
    def query_url(self) -> str:
        return (
            "https://portal.csdi.gov.hk/server/rest/services/common/"
            f"{self.dataset_id}/FeatureServer/0/query"
        )

    def to_dict(self) -> dict:
        return {**asdict(self), "query_url": self.query_url, "category": self.category_key}


@dataclass(frozen=True)
class Category:
    key: str
    name_zh: str
    group: str


# What the map and sidebar show. Several raw CSDI layers can feed one category.
CATEGORIES = (
    Category("sports_centres", "体育馆", "sports"),
    Category("ball_venues", "球类场所", "sports"),
    Category("swimming_pools", "游泳池", "sports"),
    Category("sports_grounds", "运动场与跑道", "sports"),
    Category("parks_rec", "公园与康乐场地", "leisure"),
    Category("outdoor_fitness", "户外健身设施", "leisure"),
    Category("trails", "远足径与单车径", "outdoor"),
    Category("camping", "露营与烧烤", "outdoor"),
)

BALL_SOURCE_KEYS = frozenset({"basketball", "tennis_courts", "squash_courts", "badminton_courts", "table_tennis", "grass_pitches", "hard_pitches", "bowling_greens"})

SOURCES = (
    FacilitySource("sports_centres", "体育馆", "lcsd_rcd_1629267205215_31341", 106),
    FacilitySource("outdoor_fitness", "户外健身设施", "lcsd_rcd_1670389505454_91091", 684),
    FacilitySource("basketball", "篮球场", "lcsd_rcd_1629267205215_38105", 306, category="ball_venues", default_sport="篮球场"),
    FacilitySource("tennis_courts", "网球场", "lcsd_rcd_1629267205215_84141", 53, category="ball_venues", default_sport="网球场"),
    FacilitySource("squash_courts", "壁球场", "lcsd_rcd_1629267205215_7366", 75, category="ball_venues", default_sport="壁球场"),
    FacilitySource("badminton_courts", "羽毛球场", "lcsd_rcd_1629267205214_38344", 116, category="ball_venues", default_sport="羽毛球场"),
    FacilitySource("table_tennis", "乒乓球室", "lcsd_rcd_1629267205215_47944", 126, category="ball_venues", default_sport="乒乓球"),
    FacilitySource("grass_pitches", "草地足球场", "lcsd_rcd_1629267205215_60483", 53, category="ball_venues", default_sport="足球场"),
    FacilitySource("hard_pitches", "硬地足球场", "lcsd_rcd_1629267205215_71653", 184, category="ball_venues", default_sport="足球场"),
    FacilitySource("bowling_greens", "草地滚球场", "lcsd_rcd_1629267205215_68020", 9, category="ball_venues", default_sport="草地滚球"),
    FacilitySource("swimming_pools", "游泳池", "lcsd_rcd_1634540558875_77434", 46, default_sport="游泳池"),
    FacilitySource("sports_grounds", "运动场", "lcsd_rcd_1629267205215_11128", 25, default_sport="运动场"),
    FacilitySource("walking_tracks", "健身步行径", "lcsd_rcd_1670392735866_3241", 52, category="sports_grounds", default_sport="健身步行径"),
    FacilitySource("parks", "公园及动植物公园", "lcsd_rcd_1629267205215_19292", 123, category="parks_rec"),
    FacilitySource("recreation_grounds", "康乐场地", "lcsd_rcd_1629267205215_44172", 344, category="parks_rec"),
    FacilitySource("hiking_trails", "远足径", "afcd_rcd_1665568199103_4360", 167, category="trails", default_sport="远足"),
    FacilitySource("mtb_trails", "越野单车径", "afcd_rcd_1635142692775_46557", 24, category="trails", default_sport="单车"),
    FacilitySource("campsites", "露营地", "afcd_rcd_1635133060194_82554", 41, category="camping", default_sport="露营"),
    FacilitySource("bbq_sites", "郊野公园烧烤场", "afcd_rcd_1635132752214_22438", 155, category="camping", default_sport="烧烤"),
)
