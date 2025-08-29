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
  fillable = TRUE,
  style = "--bslib-spacer: 1rem; padding-bottom: 0;",
  sidebar = sidebar(
    title = "Transcript",
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

  greeting <- "Welcome to Shiny Realtime!\n\nYou're currently muted; click the mic button to unmute, or click-and-hold the mic for push-to-talk."

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

  # Show notification when the model is generating code
  observe({
    event <- realtime_controls$event()

    if (
      event$type == "conversation.item.created" && event$item$type == "message"
    ) {
      shinychat::markdown_stream(
        "response_text",
        coro::gen(yield("")),
        operation = "replace",
        session = session
      )
    } else if (
      event$type == "conversation.item.created" &&
        event$item$type == "function_call"
    ) {
      shiny::showNotification(
        "Generating code, please wait...",
        id = event$item$id,
        closeButton = FALSE
      )
    } else if (
      event$type == "response.output_item.done" &&
        event$item$type == "function_call"
    ) {
      shiny::removeNotification(id = event$item$id)
    } else if (
      event$type == "response.text.delta" ||
        event$type == "response.audio_transcript.delta"
    ) {
      shinychat::markdown_stream(
        "response_text",
        coro::gen(yield(event$delta)),
        operation = "append",
        session = session
      )
    }
  })

  output$plot <- renderPlot({
    req(last_code())
    print("Plotting:")
    print(last_code())
    eval(parse(text = last_code()))
  })

  output$code_text <- renderText({
    req(last_code())
    last_code()
  })
}

shinyApp(ui, server)
