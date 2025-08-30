library(tidyverse)
library(shiny)
library(bslib)
library(dotenv)
library(ellmer)

source("realtime.R")

# Read prompt file
prompt <- readLines("prompt-r.md") |> paste(collapse = "\n")

# Load example datasets
samples <- list()
for (dataset in c("mpg", "diamonds", "economics", "iris", "mtcars")) {
  df <- eval(parse(text = dataset))
  if (is.data.frame(df)) {
    samples <- c(
      samples,
      paste0(
        "## ",
        dataset,
        "\n\n",
        capture.output(write.csv(head(df), "")),
        collapse = "\n"
      )
    )
  }
}

prompt <- paste0(
  prompt,
  "\n\n# Available Datasets\n\n",
  paste(samples, collapse = "\n\n")
)

ui <- page_sidebar(
  title = "Shiny Realtime Demo",
  fillable = TRUE,
  style = "--bslib-spacer: 1rem; padding-bottom: 0;",
  sidebar = sidebar(
    title = "Transcript",
    textOutput("session_cost", container = \(...) {
      div(class = "help-text", ...)
    }),
    shinychat::output_markdown_stream("response_text")
  ),
  card(
    full_screen = TRUE,
    card_header("Plot"),
    card_body(padding = 0, plotOutput("plot", fill = TRUE)),
    height = "66%"
  ),
  layout_columns(
    height = "34%",
    card(
      full_screen = TRUE,
      card_header("Code"),
      verbatimTextOutput("code_text")
    )
  ),
  realtimeUI(
    "realtime1",
    style = "z-index: 100000; margin-left: auto; margin-right: auto;",
    right = NULL
  ),
)

server <- function(input, output, session) {
  last_code <- reactiveVal()

  greeting <- "Welcome to Shiny Realtime!\n\nYou're currently muted; click the mic button to unmute, click-and-hold the mic for push-to-talk, or hold the spacebar key for push-to-talk."

  shinychat::markdown_stream(
    "response_text",
    coro::gen(yield(greeting)),
    operation = "replace",
    session = session
  )

  run_r_plot_code <- function(code) {
    beepr::beep("shutter.wav")
    last_code(code)
  }

  run_r_plot_code_tool <- ellmer::tool(
    run_r_plot_code,
    "Run R code that generates a static plot",
    arguments = list(
      code = type_string(
        "The R code to run that generates a plot. If using ggplot2, the last expression in the code should be the plot object, e.g. `p`."
      )
    )
  )

  realtime_controls <- realtimeServer(
    "realtime1",
    voice = "cedar",
    instructions = prompt,
    tools = list(run_r_plot_code_tool),
    speed = 1.1,
    output_modalities = c("text", "audio")
  )

  # Use the new event handling interface with lambda syntax

  # Handle new messages - clear transcript
  realtime_controls$on("conversation.item.created", \(event) {
    if (event$item$type == "message") {
      shinychat::markdown_stream(
        "response_text",
        coro::gen(yield("")),
        operation = "replace",
        session = session
      )
    }
  })

  # Handle function call start - show notification
  realtime_controls$on("conversation.item.created", \(event) {
    if (event$item$type == "function_call") {
      shiny::showNotification(
        "Generating code, please wait...",
        id = event$item$id,
        closeButton = FALSE
      )
    }
  })

  # Handle function call completion - remove notification
  realtime_controls$on("response.output_item.done", \(event) {
    if (event$item$type == "function_call") {
      shiny::removeNotification(id = event$item$id)
    }
  })

  # Handle text streaming
  realtime_controls$on("response.text.delta", \(event) {
    shinychat::markdown_stream(
      "response_text",
      coro::gen(yield(event$delta)),
      operation = "append",
      session = session
    )
  })

  # Handle audio transcript streaming
  realtime_controls$on("response.audio_transcript.delta", \(event) {
    shinychat::markdown_stream(
      "response_text",
      coro::gen(yield(event$delta)),
      operation = "append",
      session = session
    )
  })

  realtime_controls$on("response.done", \(event) {
    # "usage": {
    #   "total_tokens": 1977,
    #   "input_tokens": 1687,
    #   "output_tokens": 290,
    #   "input_token_details": {
    #     "text_tokens": 1636,
    #     "audio_tokens": 51,
    #     "image_tokens": 0,
    #     "cached_tokens": 1600,
    #     "cached_tokens_details": {
    #       "text_tokens": 1600,
    #       "audio_tokens": 0,
    #       "image_tokens": 0
    #     }
    #   },
    #   "output_token_details": { "text_tokens": 68, "audio_tokens": 222 }
    # }
    usage <- event$response$usage
    current_response <- c(
      input_text = usage$input_token_details$text_tokens,
      input_audio = usage$input_token_details$audio_tokens,
      input_image = usage$input_token_details$image_tokens,
      input_text_cached = usage$input_token_details$cached_tokens_details$text_tokens,
      input_audio_cached = usage$input_token_details$cached_tokens_details$audio_tokens,
      input_image_cached = usage$input_token_details$cached_tokens_details$image_tokens,
      output_text = usage$output_token_details$text_tokens,
      output_audio = usage$output_token_details$audio_tokens
    )

    cost <- sum(current_response * pricing_gpt4_realtime)
    running_cost(isolate(running_cost()) + cost)
  })

  running_cost <- reactiveVal(0)
  pricing_gpt4_realtime <- c(
    input_text = 4,
    input_audio = 32,
    input_image = 5,
    input_text_cached = 0.4,
    input_audio_cached = 0.4,
    input_image_cached = 0.5,
    output_text = 16,
    output_audio = 64
  ) /
    1e9
  pricing_gpt_4o_mini <- c(
    input_text = 0.6,
    input_audio = 10,
    input_text_cached = 0.3,
    input_audio_cached = 0.3,
    output_text = 2.4,
    output_audio = 20
  ) /
    1e9

  output$plot <- renderPlot({
    req(last_code())
    eval(parse(text = last_code()))
  })

  output$code_text <- renderText({
    req(last_code())
    last_code()
  })

  output$session_cost <- renderText({
    paste0(sprintf("Session cost: $%.6f", running_cost()))
  })
}

shinyApp(ui, server)
