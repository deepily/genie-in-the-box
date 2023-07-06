console.log( "Loading constants.js..." );
// These constants will be parsed by the multimodal munger object, and should be listed from top to bottom by longest string first.

export const VOX_CMD_CUT            = "cut";
export const VOX_CMD_COPY           = "copy";
export const VOX_CMD_PASTE          = "paste from clipboard";
export const VOX_CMD_DELETE         = "delete";
export const VOX_CMD_SELECT_ALL     = "select all";
export const VOX_EDIT_COMMANDS   = [ VOX_CMD_CUT, VOX_CMD_COPY, VOX_CMD_PASTE, VOX_CMD_DELETE, VOX_CMD_SELECT_ALL ];

export const VOX_CMD_TAB_CLOSE      = "close this tab";
export const VOX_CMD_TAB_BACK       = "go backwards";
export const VOX_CMD_TAB_FORWARD    = "go forwards";
export const VOX_CMD_TAB_REFRESH    = "refresh this tab";
export const VOX_CMD_OPEN_NEW_TAB   = "open new tab";
export const VOX_CMD_IN_CURRENT_TAB = "in current tab";
export const VOX_TAB_COMMANDS    = [ VOX_CMD_TAB_BACK, VOX_CMD_TAB_FORWARD, VOX_CMD_TAB_REFRESH, VOX_CMD_TAB_CLOSE, VOX_CMD_OPEN_NEW_TAB ];

export const VOX_CMD_OPEN_EDITOR    = "open editor";

export const VOX_CMD_OPEN_FILE      = "open file";
export const VOX_CMD_OPEN_URL_BUCKET= "open url bucket";
export const VOX_CMD_PROOFREAD      = "proofread";
export const VOX_CMD_PROOFREAD_STEM = "proof";
export const VOX_CMD_VIEW_CONSTANTS = "view constan";

export const VOX_CMD_ZOOM_IN        = "zoom in";
export const VOX_CMD_ZOOM_OUT       = "zoom out";
export const VOX_CMD_ZOOM_RESET     = "zoom reset";

export const VOX_CMD_MODE_RESET     = "reset";
export const VOX_CMD_MODE_EXIT      = "exit";
export const VOX_CMD_SET_LINK_MODE  = "set link mode";
export const LINK_MODE_DRILL_DOWN   = "drill down";
export const LINK_MODE_NEW_TAB      = "new tab";

export const LINK_MODE_CURRENT_TAB  = "current tab";
export const LINK_MODE_DEFAULT      = LINK_MODE_DRILL_DOWN;

export const VOX_CMD_SET_PROMPT_MODE  = "set prompt mode";
export const PROMPT_MODE_VERBOSE      = "verbose";
export const PROMPT_MODE_QUIET        = "quiet";
export const PROMPT_MODE_DEFAULT      = PROMPT_MODE_VERBOSE;

export const VOX_CMD_SEARCH_DDG               = "search new tab";
export const VOX_CMD_SEARCH_CURRENT_TAB_DDG   = "search current tab";
export const VOX_CMD_SEARCH_GOOGLE            = "search google new tab";
export const VOX_CMD_SEARCH_GOOGLE_CURRENT_TAB= "search google current tab";
export const VOX_CMD_SEARCH_GOOGLE_SCHOLAR    = "search google scholar new tab";
export const VOX_CMD_SEARCH_GOOGLE_SCHOLAR_CURRENT_TAB= "search google scholar current tab";
export const VOX_CMD_SEARCH_CLIPBOARD_GOOGLE_SCHOLAR = "search google scholar using clipboard";
export const VOX_CMD_SEARCH_CLIPBOARD_DDG     = "search using clipboard";
export const VOX_CMD_SEARCH_CLIPBOARD_GOOGLE  = "search google using clipboard";

export const MULTIMODAL_CONTACT_INFO  = "multimodal contact information";
export const MULTIMODAL_TEXT_PYTHON   = "multimodal python punctuation";
export const MULTIMODAL_TEXT_EMAIL    = "multimodal text email";
export const STEM_MULTIMODAL_EDITOR   = "multimodal editor";
export const STEM_MULTIMODAL_SERVER_SEARCH = "multimodal server search"

export const VOX_CMD_RUN_PROMPT           = "run prompt";
export const VOX_CMD_SUFFIX_FROM_FILE     = "from file";
export const VOX_CMD_SUFFIX_FROM_CLIPBOARD= "from clipboard";

export const VOX_CMD_SAVE_FROM_CLIPBOARD= "save from clipboard";

export const MODE_TRANSCRIPTION       = "transcription mode";
export const MODE_COMMAND             = "command mode";

export const TTS_SERVER_ADDRESS        = "http://127.0.0.1:5002";
export const GIB_SERVER_ADDRESS        = "http://127.0.0.1:7999";

export const EDITOR_URL                = "http://127.0.0.1:8080/genie-plugin-firefox/html/editor-quill.html";
export const BUCKET_URL                = "http://127.0.0.1:8080/genie-plugin-firefox/html/blank.html";
export const CONSTANTS_URL             = "http://127.0.0.1:8080/genie-plugin-firefox/js/constants.js";
export const SEARCH_URL_GOOGLE         = "https://www.google.com/search";
export const SEARCH_URL_GOOGLE_SCHOLAR = "https://scholar.google.com/scholar";
export const SEARCH_URL_DDG            = "https://www.duckduckgo.com/";

export const ZOOM_INCREMENT = 0.075;
export const ZOOM_MAX       = 5;
export const ZOOM_MIN       = 0.3;
export const ZOOM_DEFAULT   = 1;

console.log( "Loading constants.js... Done!" );