from tmdbhelper.lib.addon.plugin import get_condvisibility
from jurialmunkey.window import get_property
from tmdbhelper.lib.addon.logger import kodi_log


CV_USE_LOCAL_CONTAINER = "Skin.HasSetting(TMDbHelper.UseLocalWidgetContainer)"


CV_USE_LISTITEM = (
    "!Skin.HasSetting(TMDbHelper.ForceWidgetContainer) + "
    "!Window.IsActive(script-tmdbhelper-recommendations.xml) + ["
    "!Skin.HasSetting(TMDbHelper.UseLocalWidgetContainer) | String.IsEmpty(Window.Property(TMDbHelper.WidgetContainer))] + ["
    "Window.IsVisible(movieinformation) | "
    "Window.IsVisible(musicinformation) | "
    "Window.IsVisible(songinformation) | "
    "Window.IsVisible(addoninformation) | "
    "Window.IsVisible(pvrguideinfo) | "
    "Window.IsVisible(tvchannels) | "
    "Window.IsVisible(tvguide)]")


def container_item(container='Container.'):
    return (
        'ListItem.'
        if get_condvisibility(CV_USE_LISTITEM) else
        f'{container}ListItem({{}}).'
    )


def container(widget_id=''):
    return f'Container({widget_id}).' if widget_id else 'Container.'


def widget_id(window_id):
    window_id = window_id if get_condvisibility(CV_USE_LOCAL_CONTAINER) else None
    return get_property('WidgetContainer', window_id=window_id, is_type=int)


_dead_window_ids = {}  # caller -> window id last refused, so each run of refusals logs once


def get_live_window(window_id, caller):
    """ xbmcgui.Window(window_id), or None when that id is not an active window.
    Kodi logs "EXCEPTION: Window id does not exist" on every failed Window() even when
    Python catches it, so a poll loop retrying a dead id floods kodi.log (TheRedWizard #285).
    Checking Window.IsActive first never raises. The refused id is logged once per run. """
    if window_id and get_condvisibility(f'Window.IsActive({window_id})'):
        _dead_window_ids.pop(caller, None)
        from xbmcgui import Window
        try:
            return Window(window_id)
        except RuntimeError:
            pass
    if _dead_window_ids.get(caller) != window_id:
        _dead_window_ids[caller] = window_id
        kodi_log(f'{caller}: window id {window_id} is not active, skipped', 2)
