import unittest
from price_watch import (
    evaluate, has_at_least_1tb_ssd, has_cpu_liquid_cooling,
    has_gpu_liquid_cooling, has_m2_or_nvme, has_ram_32gb_ddr5,
    parse_price, retailer, supported_gpu,
)
from pathlib import Path
import json

class PriceWatchTests(unittest.TestCase):
    def test_price_parsing(self):
        self.assertEqual(parse_price({"extracted_price": 999.99}), 999.99)
        self.assertEqual(parse_price({"price": "$1,099.99"}), 1099.99)

    def test_retailer(self):
        self.assertEqual(retailer("Micro Center"), "Micro Center")
        self.assertEqual(retailer("Newegg.com"), "Newegg")
        self.assertIsNone(retailer("Unknown Marketplace"))

    def test_specs(self):
        self.assertTrue(has_ram_32gb_ddr5("32GB DDR5 desktop kit"))
        self.assertFalse(has_ram_32gb_ddr5("16GB DDR5 kit"))
        self.assertTrue(has_at_least_1tb_ssd("1TB NVMe SSD"))
        self.assertTrue(has_at_least_1tb_ssd("1000GB SSD"))
        self.assertFalse(has_at_least_1tb_ssd("512GB SSD"))
        self.assertTrue(has_cpu_liquid_cooling("360mm liquid cooled CPU"))
        self.assertTrue(has_gpu_liquid_cooling("AORUS WATERFORCE RTX graphics card"))
        self.assertTrue(has_m2_or_nvme("M.2 NVMe SSD"))
        self.assertFalse(has_m2_or_nvme("1TB SSD storage"))

    def test_supported_gpu(self):
        cfg=json.loads(Path("config.json").read_text(encoding="utf-8"))
        self.assertEqual(supported_gpu("RTX 5070 Ti gaming desktop",cfg),"RTX 5070 Ti")
        self.assertIsNone(supported_gpu("RTX 4060 desktop",cfg))

    def test_pc_flags_unconfirmed_cooling(self):
        cfg=json.loads(Path("config.json").read_text(encoding="utf-8"))
        item={"title":"Gaming Desktop Ryzen 7 9800X3D RTX 5070 Ti 32GB DDR5 1TB SSD",
              "source":"Newegg.com","extracted_price":2099.99,
              "product_link":"https://example.com/item"}
        match=evaluate("pc",item,cfg)
        self.assertIsNotNone(match)
        self.assertIn("GPU liquid cooling not confirmed",match["review_notes"])

    def test_refurbished_excluded(self):
        cfg=json.loads(Path("config.json").read_text(encoding="utf-8"))
        item={"title":"RTX 5070 Ti Graphics Card Refurbished","source":"Newegg.com",
              "extracted_price":799.99,"product_link":"https://example.com/item"}
        self.assertIsNone(evaluate("gpu",item,cfg))

if __name__ == "__main__":
    unittest.main()
