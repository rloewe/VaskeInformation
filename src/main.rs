mod laundry;
use laundry::{Laundry, MachineType};

use serenity::{
    async_trait,
    framework::standard::{
        macros::{command, group, hook},
        CommandResult, StandardFramework,
    },
    model::{channel::Message, gateway::Ready, id::UserId},
    prelude::*,
};
use std::sync::Arc;
use tokio::{
    sync::RwLock,
    time::{sleep, Duration},
};

use std::env;

struct LaundryContainer;

impl TypeMapKey for LaundryContainer {
    type Value = Arc<RwLock<Laundry>>;
}

#[group]
#[commands(status, need, using)]
struct Wash;

struct Handler;

#[async_trait]
impl EventHandler for Handler {
    /*async fn message(&self, _ctx: Context, msg: Message) {
        println!("Got message '{}' in {}", msg.content, msg.channel_id);
    }*/

    async fn ready(&self, _ctx: Context, ready: Ready) {
        println!("{} is connected", ready.user.name);
    }
}

#[hook]
async fn unknown(_ctx: &Context, msg: &Message, name: &str) {
    println!("Got input {} with command name {}", msg.content, name);
}

#[command]
async fn status(ctx: &Context, msg: &Message) -> CommandResult {
    println!("Got status");

    let lock = {
        let data_read = ctx.data.read().await;
        data_read
            .get::<LaundryContainer>()
            .expect("Expected Laundry in TypeMap")
            .clone()
    };

    let output = {
        let mut laundry = lock.write().await;

        laundry.get_machines_pretty().await
    };

    msg.reply(ctx, format!("```\n{}```", output)).await?;

    Ok(())
}

#[command]
async fn need(ctx: &Context, msg: &Message) -> CommandResult {
    let command_offset = msg.content.find("need").unwrap();
    let rest = &msg.content[command_offset + 4..].trim().to_lowercase();
    if rest == &"" {
        msg.reply(ctx, "What do you need? Your requst is empty 🧐")
            .await?;
        return Ok(());
    }
    let machine_type = match rest.as_str() {
        "washer" => MachineType::Washer,
        "dryer" => MachineType::Dryer,
        _ => MachineType::Other(rest.to_string()),
    };
    if machine_type == MachineType::Washer || machine_type == MachineType::Dryer {
        if is_type_available(ctx, &machine_type).await {
            msg.reply(ctx, "There is already a machine of that type available. You do know, that you can check all machines with status, right? 😉").await?;
            msg.react(ctx, '😂').await?;

            return Ok(());
        }
        msg.react(ctx, '👍').await?;
        while !is_type_available(ctx, &machine_type).await {
            sleep(Duration::from_secs(10)).await;
        }
        msg.reply(
            ctx,
            format!(
                "There is now a {} available for you! Hurry before someone else takes it",
                rest
            ),
        )
        .await?;
    } else {
        msg.reply(ctx, "I do not understand that machine type. 🤔")
            .await?;
    }

    Ok(())
}

#[command]
async fn using(ctx: &Context, msg: &Message) -> CommandResult {
    let command_offset = msg.content.find("using").unwrap();
    let rest = &msg.content[command_offset + 5..].trim().to_lowercase();
    println!("{}", rest);
    if rest == &"" {
        msg.reply(ctx, "What are you using? Your request is empty 🧐")
            .await?;
        return Ok(());
    }
    if !does_exist(ctx, rest.to_string()).await {
        msg.reply(
            ctx,
            "The machine, you are looking for, does not exist. I am confused 🤔",
        )
        .await?;
        return Ok(());
    }
    if is_available(ctx, rest.to_string()).await {
        msg.reply(ctx, "The machine is already done. Is typing difficult or did you forget to set a reminder earlier? 🧐").await?;
        msg.react(ctx, '😂').await?;
        return Ok(());
    }

    msg.react(ctx, '👍').await?;

    while !is_available(ctx, rest.to_string()).await {
        sleep(Duration::from_secs(10)).await;
    }

    msg.reply(
        ctx,
        "Your laundry is now done. 🙌 Maybe you should go get it?",
    )
    .await?;

    Ok(())
}

async fn is_available(ctx: &Context, name: String) -> bool {
    let lock = {
        let data_read = ctx.data.read().await;
        data_read
            .get::<LaundryContainer>()
            .expect("Expected Laundry in TypeMap")
            .clone()
    };

    {
        let mut laundry = lock.write().await;

        laundry.is_machine_available(name).await
    }
}

async fn is_type_available(ctx: &Context, machine_type: &MachineType) -> bool {
    let lock = {
        let data_read = ctx.data.read().await;
        data_read
            .get::<LaundryContainer>()
            .expect("Expected Laundry in TypeMap")
            .clone()
    };

    {
        let mut laundry = lock.write().await;

        laundry.is_type_available(&machine_type).await
    }
}

async fn does_exist(ctx: &Context, name: String) -> bool {
    let lock = {
        let data_read = ctx.data.read().await;
        data_read
            .get::<LaundryContainer>()
            .expect("Expected Laundry in TypeMap")
            .clone()
    };

    {
        let mut laundry = lock.write().await;

        laundry.does_machine_exist(name).await
    }
}

#[tokio::main]
async fn main() {
    let token = "";
    let client_id = UserId(0);
    let framework = StandardFramework::new()
        .configure(|c| {
            c.on_mention(Some(client_id))
                .prefix("")
                .with_whitespace(true)
        })
        .unrecognised_command(unknown)
        .group(&WASH_GROUP);

    let mut client = Client::builder(&token)
        .event_handler(Handler)
        .framework(framework)
        .await
        .expect("Error during creation of client");

    {
        let mut data = client.data.write().await;

        data.insert::<LaundryContainer>(Arc::new(RwLock::new(Laundry::new())))
    }

    if let Err(why) = client.start().await {
        println!("Client error: {:?}", why);
    }
}
