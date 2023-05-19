import logging

from .path import TorrentPath

from module.models import BangumiData
from module.conf import settings

logger = logging.getLogger(__name__)


class DownloadClient(TorrentPath):
    def __init__(self):
        super().__init__()
        self.client = self.__getClient()
        self.authed = False

    @staticmethod
    def __getClient():
        # TODO 多下载器支持
        type = settings.downloader.type
        host = settings.downloader.host
        username = settings.downloader.username
        password = settings.downloader.password
        ssl = settings.downloader.ssl
        if type == "qbittorrent":
            from .client.qb_downloader import QbDownloader
            return QbDownloader(host, username, password, ssl)
        else:
            raise Exception(f"Unsupported downloader type: {type}")

    def __enter__(self):
        if not self.authed:
            logger.debug("Authing to downloader...")
            self.auth()
            logger.debug("Authed.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.authed:
            self.client.logout()
            self.authed = False

    def auth(self):
        self.authed = self.client.auth()

    def init_downloader(self):
        prefs = {
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 500,
            "rss_processing_enabled": True,
            "rss_refresh_interval": 30,
        }
        self.client.prefs_init(prefs=prefs)
        try:
            self.client.add_category("BangumiCollection")
        except Exception as e:
            logger.warning("Cannot add new category, maybe already exists.")
            logger.debug(e)
        if settings.downloader.path == "":
            prefs = self.client.get_app_prefs()
            settings.downloader.path = self._join_path(prefs["save_path"], "Bangumi")

    def set_rule(self, data: BangumiData):
        rule = {
            "enable": True,
            "mustContain": data.title_raw,
            "mustNotContain": "|".join(data.filter),
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": data.rss_link,
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": False,
            "assignedCategory": "Bangumi",
            "savePath": self._gen_save_path(data),
        }
        rule_name = self._rule_name(data)
        self.client.rss_set_rule(rule_name=rule_name, rule_def=rule)
        logger.info(f"Add {data.official_title} Season {data.season} to auto download rules.")

    def add_collection_feed(self, rss_link, item_path):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)
        logger.info("Add Collection RSS Feed successfully.")

    def set_rules(self, bangumi_info: list[BangumiData]):
        logger.debug("Start adding rules.")
        for info in bangumi_info:
            if not info.added:
                self.set_rule(info)
                info.added = True
        logger.debug("Finished.")

    def get_torrent_info(self, category="Bangumi"):
        return self.client.torrents_info(status_filter="completed", category=category)

    def rename_torrent_file(self, _hash, old_path, new_path) -> bool:
        logger.info(f"{old_path} >> {new_path}")
        return self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path
        )

    def delete_torrent(self, hashes):
        self.client.torrents_delete(hashes)
        logger.info(f"Remove torrents.")

    def add_torrent(self, torrent: dict):
        self.client.torrents_add(
            urls=torrent["url"], save_path=torrent["save_path"], category="Bangumi"
        )

    def move_torrent(self, hashes, location):
        self.client.move_torrent(hashes=hashes, new_location=location)

    def add_rss_feed(self, rss_link, item_path="Mikan_RSS"):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)
        logger.info("Add RSS Feed successfully.")

    def get_download_rules(self):
        return self.client.get_download_rule()

    def get_torrent_path(self, hashes):
        return self.client.get_torrent_path(hashes)

    def set_category(self, hashes, category):
        self.client.set_category(hashes, category)

    def remove_rule(self, rule_name):
        self.client.remove_rule(rule_name)
        logger.info(f"Delete rule: {rule_name}")