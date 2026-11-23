# Vlastní katalog aplikací pro LG webOS / Glasshouse

Tento repozitář publikuje katalog `repo.json`, který lze přidat v Glasshouse do **Apps → Other app catalogs**. Katalog sjednocuje aplikace z několika nezávislých GitHub projektů. GitHub Actions pravidelně kontroluje jejich poslední stabilní vydání a při změně aktualizuje `repo.json`.

## Přidané aplikace

Katalog aktuálně sleduje tyto aplikace:

| Aplikace | ID webOS | Zdroj |
|---|---|---|
| ytnative | `io.github.danzig666.ytnative` | [danzig666/ytnative](https://github.com/danzig666/ytnative) |
| Origin | `io.github.betterstremio.origin` | [betterstremio/origin](https://github.com/betterstremio/origin) |
| Pley | `app.pley.tv` | [pley-media-server/pley](https://github.com/pley-media-server/pley) |
| PlxNative | `com.beb.plxnative` | [plxnative/plx-native](https://github.com/plxnative/plx-native) |
| Twitch AdFree | `twitch.adamffdev.v1` | [adamff-dev/twitch-adfree-webos](https://github.com/adamff-dev/twitch-adfree-webos) |
| LG Input Hook | `org.webosbrew.inputhook` | [Simon34545/lginputhook](https://github.com/Simon34545/lginputhook) |
| YouTube RF1705 | `youtube.leanback.v4` | [RF1705/youtube-webos-cobalt-adfree](https://github.com/RF1705/youtube-webos-cobalt-adfree) |
| NHK World | `org.mondy.nhkworld` | [mondychan/nhk-world](https://github.com/mondychan/nhk-world) |

Všechny položky jsou vybírány jako stabilní vydání. Skript vyhledá přesně pojmenovaný webOS IPK soubor, načte jeho SHA-256 z GitHub Release API (případně jej dopočítá stažením balíčku) a vytvoří manifest, který Glasshouse umí zpracovat.

## Vytvoření repozitáře na GitHubu

Po rozbalení ZIP archivu otevři terminál (WSL Ubuntu, Git Bash nebo Linux) v adresáři `glasshouse-webos-catalog` a spusť:

```bash
git init -b main
git add .
git commit -m "Initial Glasshouse webOS app catalogue"
```

Potom se přihlas do GitHub CLI (stačí jednou na daném počítači):

```bash
gh auth login
```

Vyber GitHub.com, HTTPS a přihlášení přes webový prohlížeč. Následně založ veřejný repozitář a odešli do něj obsah:

```bash
gh repo create webos-tv-app-catalog --public --source=. --remote=origin --push
```

Repozitář musí mít výchozí větev `main`. Pokud chceš jiné jméno, změň `webos-tv-app-catalog` v posledním příkazu.

## Přidání do Glasshouse

V Glasshouse otevři **Apps → Other app catalogs → Add catalog** a zadej adresu GitHub repozitáře:

```text
https://github.com/TVUJ-GITHUB-UCET/webos-tv-app-catalog
```

Není potřeba zadávat `/tree/main`. Glasshouse si z adresy GitHub repozitáře odvodí URL `repo.json` na výchozí větvi. Alternativně můžeš vložit přímou URL:

```text
https://raw.githubusercontent.com/TVUJ-GITHUB-UCET/webos-tv-app-catalog/main/repo.json
```

Po přidání se aplikace zobrazí v **Other app catalogs**. Glasshouse porovnává verze podle webOS app ID a nabídne **Update**, jakmile katalog nabídne vyšší verzi.

## Automatické aktualizace

Soubor `.github/workflows/update-catalog.yml` spouští automatickou kontrolu každých šest hodin a také umožňuje ruční spuštění přes **GitHub → Actions → Update Glasshouse app catalogue → Run workflow**.

Workflow používá vestavěný `GITHUB_TOKEN`; není nutné vytvářet ani ukládat žádný vlastní token nebo secret. Má pouze oprávnění `contents: write`, aby mohl změněný `repo.json` commitnout zpět do repozitáře.

Skript `scripts/update_catalog.py` čte zdroje z `catalog-sources.json`. Když upstream vydá novou verzi, aktualizuje číslo verze, URL IPK, velikost balíčku a SHA-256. Pokud některý upstream nemá stabilní vydání, odpovídající IPK nebo platný hash, běh skončí chybou a původní katalog zůstane zachovaný. Tím se předejde publikování neúplné aktualizace.

Lokální aktualizaci lze spustit také ručně (vyžaduje Python 3.10+ a internetové připojení):

```bash
python scripts/update_catalog.py
python -m json.tool repo.json > /dev/null
```

Potom změny odešli:

```bash
git add repo.json
git commit -m "chore(catalog): refresh application versions"
git push
```

## Bezpečnost a důvěra

Přidáním katalogu dáváš Glasshouse možnost nabídnout instalaci balíčků uvedených v tomto repozitáři. Katalog proto obsahuje pouze pevně definované oficiální upstream repozitáře, přesně vybrané IPK artefakty a SHA-256 kontrolní součty. Skript neinstaluje žádné aplikace sám; pouze udržuje katalogová metadata. Samotnou instalaci nebo aktualizaci stále potvrzuješ v Glasshouse.

Před prvním použitím doporučuji zkontrolovat seznam zdrojů v `catalog-sources.json` a workflow v `.github/workflows/update-catalog.yml`.
