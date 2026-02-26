import typer
from typing import Optional
import checks
import config_loader
import plugins_loader

app = typer.Typer(name="bee-pagoda")

@app.command()
def run(profile: str = "balanced", categories: Optional[str] = None):
    checks.verify_deps()
    config = config_loader.load_config(f"profiles/{profile}.yaml")
    cats = categories.split(",") if categories else config.get("categories", ["cpu", "gpu", "ai", "memory", "disk"])
    for cat in cats:
        plugins = plugins_loader.load_plugins(cat)
        # TODO: Run plugins
    typer.echo("Benchmark backbone complete.")

if __name__ == "__main__":
    app()
