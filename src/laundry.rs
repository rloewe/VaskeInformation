use chrono::{prelude::*, Duration, Timelike};
use cookie_store::{CookieStore, CookieStoreMutex};
use prettytable::{Cell, Row, Table};
use reqwest;
use soup::prelude::*;
use std::{io::Write, sync::Arc, time::SystemTime};

pub struct Laundry {
    machines: Vec<Machine>,
    last_updated: SystemTime,
    client: reqwest::Client,
    cookie_store: Arc<CookieStoreMutex>,
    url: String,
}

struct Machine {
    machine_type: MachineType,
    name: String,
    availability: Status,
}

#[derive(PartialEq)]
pub enum Status {
    Free,
    InUse {
        start_time: DateTime<Local>,
        time_left: Option<u8>,
    },
}

#[derive(PartialEq)]
pub enum MachineType {
    Washer,
    Dryer,
    Other(String),
}
impl std::fmt::Display for MachineType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MachineType::Washer => write!(f, "washer"),
            MachineType::Dryer => write!(f, "dryer"),
            MachineType::Other(name) => write!(f, "{}", name),
        }
    }
}

impl Laundry {
    pub fn new(url: String) -> Laundry {
        let cookie_store = {
            match std::fs::File::open("cookies.json") {
                Ok(file) => {
                    let reader = std::io::BufReader::new(file);
                    CookieStore::load_json(reader).unwrap()
                }
                Err(_) => CookieStore::default(),
            }
        };
        let cookie_store = CookieStoreMutex::new(cookie_store);
        let cookie_store = Arc::new(cookie_store);
        Laundry {
            machines: vec![],
            last_updated: SystemTime::UNIX_EPOCH,
            client: reqwest::Client::builder()
                .cookie_provider(cookie_store.clone())
                .build()
                .unwrap(),
            cookie_store,
            url,
        }
    }

    async fn update_machines(&mut self) {
        let body = self.client.get(&self.url).send().await.unwrap();
        {
            // Write store back to disk
            let mut writer = std::fs::File::create("cookies.json")
                .map(std::io::BufWriter::new)
                .unwrap();
            let store = self.cookie_store.lock().unwrap();
            for cookie in store.iter_any() {
                writeln!(writer, "{}", serde_json::to_string(cookie).unwrap()).unwrap();
            }
            store.save_json(&mut writer).unwrap();
            writer.flush().unwrap();
        }
        let soup = Soup::new(&body.text().await.unwrap());
        let elements = soup.tag("tr").attr("bgcolor", true).find_all();
        self.machines.clear();
        for element in elements {
            let children = element.tag("td").find_all().collect::<Vec<_>>();
            let name = children[0].text().trim().to_string();
            let status = children[2].text().trim().to_lowercase();
            let status = match status.as_str() {
                "fri" => Status::Free,
                _ => {
                    // ca. 2 min. | kl. 09:22

                    let time_left = children[3]
                        .text()
                        .trim()
                        .split_ascii_whitespace()
                        .nth(1)
                        .unwrap()
                        .parse::<u8>()
                        .unwrap();
                    let start_time = children[4]
                        .text()
                        .trim()
                        .split_ascii_whitespace()
                        .nth(1)
                        .unwrap()
                        .split(":")
                        .map(|x| x.parse::<u32>().unwrap())
                        .collect::<Vec<_>>();

                    Status::InUse {
                        start_time: Laundry::guess_time(start_time[0], start_time[1]),
                        time_left: Some(time_left),
                    }
                }
            };

            let machine = Machine {
                machine_type: match name.split(" ").next().unwrap().to_lowercase().as_str() {
                    "vask" => MachineType::Washer,
                    "tumbler" => MachineType::Dryer,
                    other => MachineType::Other(other.to_string()),
                },
                name: name,
                availability: status,
            };
            self.machines.push(machine);
        }
        self.last_updated = SystemTime::now()
    }

    async fn get_machines(&mut self) -> &[Machine] {
        if self.last_updated.elapsed().unwrap().as_secs() > 40 {
            self.update_machines().await;
        }
        &self.machines
    }

    pub async fn does_machine_exist(&mut self, name: String) -> bool {
        let machines = self.get_machines().await;
        machines
            .iter()
            .any(|m| m.name.to_lowercase() == name.to_lowercase())
    }

    pub async fn is_machine_available(&mut self, name: String) -> bool {
        let machines = self.get_machines().await;
        match machines.iter().find(|p| p.name.to_lowercase() == name) {
            Some(machine) => machine.availability == Status::Free,
            None => {
                println!("No, machine with that name");
                false
            }
        }
    }

    pub async fn is_type_available(&mut self, machine_type: &MachineType) -> bool {
        let machines = self.get_machines().await;
        machines
            .iter()
            .any(|m| m.machine_type == *machine_type && m.availability == Status::Free)
    }

    pub async fn get_machines_pretty(&mut self) -> String {
        let machines = self.get_machines().await;

        let mut table = Table::new();
        table.add_row(Row::new(vec![
            Cell::new("Name"),
            Cell::new("Type"),
            Cell::new("Status"),
            Cell::new("Started"),
            Cell::new("Remaning"),
        ]));
        for machine in machines {
            let mut row = Row::new(vec![
                Cell::new(&machine.name),
                Cell::new(&machine.machine_type.to_string()),
            ]);
            match machine.availability {
                Status::Free => {
                    row.add_cell(Cell::new("Free"));
                }
                Status::InUse {
                    start_time,
                    time_left,
                } => {
                    row.add_cell(Cell::new("In Use"));
                    row.add_cell(Cell::new(&start_time.format("%H:%M").to_string()));
                    let time_left_string = match time_left {
                        Some(time) => format!("{} min left", time),
                        None => "Unknown".to_string(),
                    };
                    row.add_cell(Cell::new(&time_left_string));
                }
            }
            table.add_row(row);
        }

        table.to_string()
    }

    fn guess_time(hour: u32, minute: u32) -> DateTime<Local> {
        let now = Local::now();
        let dumb_guess = now
            .with_hour(hour)
            .unwrap()
            .with_minute(minute)
            .unwrap()
            .with_second(0)
            .unwrap()
            .with_nanosecond(0)
            .unwrap();

        (-1..=1)
            .map(|n| dumb_guess + Duration::days(n))
            .min_by_key(|&d| (d - now).num_seconds().abs())
            .unwrap()
    }
}
